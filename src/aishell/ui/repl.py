"""Interactive REPL session using prompt_toolkit and Rich."""

import os
import sys
import time
import uuid
from typing import Callable, Iterable, List, Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.filters import has_focus
from prompt_toolkit.formatted_text import to_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel

from aishell.config.settings import AishellSettings, get_settings
from aishell.ui.banner import format_prompt, get_prompt_style, render_banner
from aishell.ui.history import SQLiteHistory
from aishell.ui.renderer import RichStreamRenderer


class InteractiveREPL:
    """Interactive shell assistant and command REPL.

    Provides multiline input, SQLite history search (Ctrl+R), styled status prompts,
    safe stream interrupt routing (Ctrl+C), and execution dispatch per REPL-01, REPL-02, REPL-04.
    """

    def __init__(
        self,
        settings: Optional[AishellSettings] = None,
        console: Optional[Console] = None,
        history: Optional[SQLiteHistory] = None,
        executor_fn: Optional[Callable[[str], int]] = None,
        pt_input=None,
        pt_output=None,
    ) -> None:
        self.settings = settings or get_settings()
        self.console = console or Console()
        self.session_id = str(uuid.uuid4())[:8]
        self.history = history or SQLiteHistory(session_id=self.session_id)
        self.renderer = RichStreamRenderer(console=self.console)
        self.executor_fn = executor_fn

        self.last_interrupt_time: float = 0.0
        self.is_streaming: bool = False
        self.kb = self._create_keybindings()

        try:
            self.session: PromptSession = PromptSession(
                history=self.history,
                key_bindings=self.kb,
                style=get_prompt_style(),
                multiline=True,
                enable_history_search=True,
                input=pt_input,
                output=pt_output,
            )
        except Exception:
            from prompt_toolkit.output import DummyOutput

            self.session = PromptSession(
                history=self.history,
                key_bindings=self.kb,
                style=get_prompt_style(),
                multiline=True,
                enable_history_search=True,
                input=pt_input,
                output=DummyOutput(),
            )

    def _create_keybindings(self) -> KeyBindings:
        """Configure multiline keybindings per D-02: Enter executes, Alt+Enter / `\\` newline."""
        kb = KeyBindings()

        @kb.add("escape", "enter")
        @kb.add("c-j")
        def _insert_newline(event):
            """Insert a newline buffer on Alt+Enter or Ctrl+J."""
            event.current_buffer.insert_text("\n")

        @kb.add("enter")
        def _handle_enter(event):
            """Submit on Enter unless line ends with trailing backslash."""
            buf = event.current_buffer
            text = buf.text
            # If buffer ends with trailing backslash, replace it with newline
            if text.endswith("\\"):
                buf.delete_before_cursor(count=1)
                buf.insert_text("\n")
            else:
                buf.validate_and_handle()

        return kb

    def get_prompt_tokens(self) -> list:
        """Return dynamic prompt tokens reflecting current working directory and model."""
        return format_prompt(
            cwd=os.getcwd(),
            model_name=self.settings.general.model,
        )

    def handle_meta_command(self, cmd: str) -> bool:
        """Handle internal meta commands (:exit, :quit, /clear, /help).

        Returns True if REPL should terminate, False otherwise.
        """
        clean = cmd.strip().lower()
        if clean in (":exit", ":quit", "/exit", "/quit", "exit", "quit"):
            self.console.print("[dim]Goodbye![/dim]")
            return True
        elif clean in (":clear", "/clear", "clear"):
            self.console.clear()
            return False
        elif clean in (":help", "/help", "help"):
            self._print_help()
            return False
        return False

    def _print_help(self) -> None:
        """Print interactive REPL help guide."""
        content = (
            "[bold cyan]aishell Interactive REPL Guide[/bold cyan]\n\n"
            "• [bold green]Natural Language Query:[/bold green] Type your question or intent directly\n"
            "• [bold green]Direct Shell Command:[/bold green] Prefix with [bold yellow]![/bold yellow] or run standard builtins (`cd`, `export`)\n"
            "• [bold green]Multiline Input:[/bold green] Press [bold yellow]Alt+Enter[/bold yellow] or end line with trailing [bold yellow]\\[/bold yellow]\n"
            "• [bold green]History Search:[/bold green] Press [bold yellow]Ctrl+R[/bold yellow] to reverse search command history\n"
            "• [bold green]Interrupt Stream:[/bold green] Press [bold yellow]Ctrl+C[/bold yellow] to halt active generation\n"
            "• [bold green]Exit Session:[/bold green] Type [bold yellow]:exit[/bold yellow] or press [bold yellow]Ctrl+D[/bold yellow]"
        )
        self.console.print(Panel(content, border_style="cyan", expand=False))

    def dispatch_input(self, user_input: str) -> None:
        """Dispatch user input to shell executor or stream renderer."""
        raw = user_input.strip()
        if not raw:
            return

        # Check for meta commands first
        if raw.startswith(":") or raw.startswith("/") or raw in ("exit", "quit", "help", "clear"):
            if self.handle_meta_command(raw):
                raise EOFError()
            return

        # Check for direct shell command prefix or common builtins
        is_direct_shell = raw.startswith("!") or raw.startswith("$")
        cmd_to_run = raw[1:].strip() if is_direct_shell else raw

        if is_direct_shell or raw.startswith("cd ") or raw.startswith("export ") or raw.startswith("unset "):
            if self.executor_fn:
                try:
                    self.executor_fn(cmd_to_run)
                except Exception as exc:
                    self.renderer.render_error(str(exc))
            else:
                from aishell.cli import execute_pipeline

                execute_pipeline(cmd_to_run)
            return

        # Natural language query - Stream tokens (Dispatches to Phase 3 LLM in next phase)
        self.is_streaming = True
        try:
            tokens = [f"I received your query: **{raw}**\n\n*(AI model provider integration will stream here in Phase 3)*\n"]
            self.renderer.stream_markdown(tokens)
        finally:
            self.is_streaming = False

    def run(self) -> None:
        """Run interactive REPL event loop."""
        render_banner(self.console, self.settings)

        while True:
            try:
                prompt_tokens = self.get_prompt_tokens()
                user_input = self.session.prompt(prompt_tokens)
                self.dispatch_input(user_input)
                # Reset consecutive interrupt timer after successful input
                self.last_interrupt_time = 0.0

            except KeyboardInterrupt:
                if self.is_streaming:
                    # Cancel streaming token generation immediately without killing session per REPL-04
                    self.is_streaming = False
                    self.console.print("\n[dim yellow]^C (generation cancelled)[/dim yellow]")
                    continue

                # Empty prompt buffer interrupt handling per D-03
                now = time.time()
                if now - self.last_interrupt_time <= 1.5:
                    self.console.print("\n[dim]Exiting aishell...[/dim]")
                    break
                else:
                    self.last_interrupt_time = now
                    self.console.print("\n[dim](Press Ctrl+C again or Ctrl+D to exit)[/dim]")
                    continue

            except EOFError:
                self.console.print("\n[dim]Exiting aishell...[/dim]")
                break
            except Exception as exc:
                self.renderer.render_error(f"Unexpected error: {exc}")
