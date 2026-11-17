"""Interactive REPL session using prompt_toolkit and Rich."""

import os
import re
import shutil
import sys
import time
import uuid
from typing import Callable, Iterable, List, Optional, Tuple
from prompt_toolkit import PromptSession
from prompt_toolkit.filters import has_focus
from prompt_toolkit.formatted_text import to_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel

from aishell.config.settings import AishellSettings, get_settings
from aishell.conversation.manager import ConversationManager
from aishell.diagnostics.engine import DiagnosticEngine
from aishell.diagnostics.remediation import RemediationController
from aishell.providers.base import BaseProvider
from aishell.safety.gate import SafetyGate
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
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        provider: Optional[BaseProvider] = None,
        pt_input=None,
        pt_output=None,
    ) -> None:
        self.settings = settings or get_settings()
        self.console = console or Console()
        self.session_id = str(uuid.uuid4())[:8]
        self.history = history or SQLiteHistory(session_id=self.session_id)
        self.safety_gate = SafetyGate(console=self.console)
        self.renderer = RichStreamRenderer(console=self.console)
        self.executor_fn = executor_fn

        from aishell.providers.factory import get_provider

        if provider:
            self.provider = provider
        else:
            p_name = provider_name or self.settings.general.default_provider
            m_name = model_name or self.settings.general.model
            self.provider = get_provider(
                name=p_name,
                model=m_name,
                settings=self.settings,
                validate=False,
            )

        self.conversation = ConversationManager()
        self.diagnostic_engine = DiagnosticEngine(provider=self.provider)
        self.remediation_controller = RemediationController()

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

    def _trigger_remediation(self, command: str, exit_code: int, output: str) -> int:
        """Trigger bounded remediation loop on command failure."""
        self.diagnostic_engine._provider = self.provider

        runner = self.executor_fn
        if runner is None:
            from aishell.cli import execute_pipeline
            runner = lambda c: execute_pipeline(c, session_id=self.session_id)

        return self.remediation_controller.run_remediation_loop(
            failed_command=command,
            exit_code=exit_code,
            output=output,
            diagnostic_engine=self.diagnostic_engine,
            safety_gate=self.safety_gate,
            executor_fn=runner,
            console=self.console,
            prompt_session=self.session,
        )

    def _execute_with_remediation(self, command: str) -> int:
        """Execute command and trigger remediation loop if it terminates with non-zero exit code."""
        if self.executor_fn:
            try:
                res = self.executor_fn(command)
            except Exception as exc:
                self.renderer.render_error(str(exc))
                res = 1
        else:
            from aishell.cli import execute_pipeline_capture
            res = execute_pipeline_capture(command, session_id=self.session_id)

        exit_code = 0
        output = ""
        if isinstance(res, tuple) and len(res) == 2:
            exit_code, output = res
        elif isinstance(res, int):
            exit_code = res
            output = f"Command exited with code {exit_code}"

        self._last_execution = (command, exit_code, output)
        if exit_code != 0 and exit_code != 130:
            return self._trigger_remediation(command, exit_code, output)
        return exit_code

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
        """Return clean prompt tokens: 'aishell $ ' or 'aishell # '."""
        return format_prompt()

    def handle_meta_command(self, cmd: str) -> bool:
        """Handle internal meta commands (:exit, :quit, /clear, /help, /provider, /model).

        Returns True if REPL should terminate, False otherwise.
        """
        parts = cmd.strip().split(maxsplit=1)
        action = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else None

        if action in (":exit", ":quit", "/exit", "/quit", "exit", "quit"):
            return True
        elif action in (":clear", "/clear", "clear"):
            self.console.clear()
            self.conversation.clear()
            return False
        elif action in (":help", "/help", "help"):
            self._print_help()
            return False
        elif action in (":provider", "/provider", "provider"):
            from aishell.providers.factory import get_provider, get_supported_providers

            if arg:
                try:
                    self.provider = get_provider(name=arg, settings=self.settings, validate=False)
                    self.diagnostic_engine._provider = self.provider
                    self.console.print(f"[green]Switched active provider to '{self.provider.name}' (model: {self.provider.model})[/green]")
                except Exception as exc:
                    self.renderer.render_error(str(exc))
            else:
                supported = ", ".join(get_supported_providers())
                self.console.print(f"[bold cyan]Active provider:[/bold cyan] {self.provider.name} (model: {self.provider.model})\n[dim]Supported: {supported}[/dim]")
            return False
        elif action in (":model", "/model", "model"):
            from aishell.providers.factory import get_provider

            if arg:
                try:
                    self.provider = get_provider(
                        name=self.provider.name,
                        model=arg,
                        settings=self.settings,
                        validate=False,
                    )
                    self.diagnostic_engine._provider = self.provider
                    self.console.print(f"[green]Switched model to '{self.provider.model}' on provider '{self.provider.name}'[/green]")
                except Exception as exc:
                    self.renderer.render_error(str(exc))
            else:
                self.console.print(f"[bold cyan]Active model:[/bold cyan] {self.provider.model} (provider: {self.provider.name})")
            return False
        elif action in (":context", "/context", "context"):
            from aishell.context.display import render_context_table
            from aishell.context.inspector import inspect_system_context

            ctx_info = inspect_system_context(cwd=os.getcwd())
            render_context_table(ctx_info, console=self.console)
            return False
        return False

    def _print_help(self) -> None:
        """Print interactive REPL help guide."""
        content = (
            "[bold cyan]aishell Interactive REPL Guide[/bold cyan]\n\n"
            "• [bold green]Natural Language Query:[/bold green] Type your question or intent directly\n"
            "• [bold green]Direct Shell Command:[/bold green] Prefix with [bold yellow]![/bold yellow] or run standard builtins (`cd`, `export`)\n"
            "• [bold green]System Context:[/bold green] Type [bold yellow]/context[/bold yellow] to inspect host facts and sanitized environment\n"
            "• [bold green]Switch Provider / Model:[/bold green] [bold yellow]/provider <name>[/bold yellow] or [bold yellow]/model <name>[/bold yellow]\n"
            "• [bold green]Multiline Input:[/bold green] Press [bold yellow]Alt+Enter[/bold yellow] or end line with trailing [bold yellow]\\[/bold yellow]\n"
            "• [bold green]History Search:[/bold green] Press [bold yellow]Ctrl+R[/bold yellow] to reverse search command history\n"
            "• [bold green]Interrupt Stream:[/bold green] Press [bold yellow]Ctrl+C[/bold yellow] to halt active generation\n"
            "• [bold green]Exit Session:[/bold green] Type [bold yellow]:exit[/bold yellow] or press [bold yellow]Ctrl+D[/bold yellow]"
        )
        self.console.print(Panel(content, border_style="cyan", expand=False))

    _DIRECT_SHELL_COMMANDS = frozenset({
        "ls", "ll", "la", "df", "du", "free", "ps", "top", "htop", "btop",
        "uptime", "whoami", "id", "uname", "pwd", "echo", "cat", "head",
        "tail", "less", "more", "grep", "egrep", "fgrep", "rg", "awk", "sed",
        "sort", "uniq", "wc", "cut", "tr", "mkdir", "rmdir", "rm", "cp", "mv",
        "touch", "ln", "chmod", "chown", "chgrp", "tar", "gzip", "gunzip",
        "zip", "unzip", "curl", "wget", "ping", "traceroute", "dig",
        "nslookup", "ip", "ifconfig", "ss", "netstat", "lsof", "lsblk",
        "fdisk", "mount", "umount", "git", "docker", "docker-compose",
        "kubectl", "systemctl", "journalctl", "service", "apt", "apt-get",
        "dpkg", "dnf", "yum", "pacman", "pip", "pip3", "pipx", "uv", "python",
        "python3", "node", "npm", "npx", "sudo", "su", "vi", "vim", "nano",
        "which", "whereis", "env", "printenv", "date", "cal", "kill", "pkill",
        "killall", "clear", "reset", "history", "man", "stat", "file", "tee",
        "xargs", "jq", "cd", "export", "unset", "alias", "unalias", "source",
    })

    _WAKE_PREFIX_RE = re.compile(r"^(?:ais|ai)\b[:,\s]*(.*)$", re.IGNORECASE)
    _CONVERSATIONAL_WAKE_RE = re.compile(r"^(?:hi|hello|hey|please)\b[,:\s]*(.*)$", re.IGNORECASE)

    def _classify_input(self, raw: str) -> Tuple[str, str]:
        """Classify user input into ('shell', command) or ('ai', query).

        Direct shell commands (e.g. 'ls', 'df -h', '!cmd', 'cd /tmp') run directly
        without waking the AI. AI is invoked for explicit wake-up prefixes ('hi,',
        'please', 'ais', '?') or natural language queries.
        """
        if raw.startswith("!") or raw.startswith("$"):
            return ("shell", raw[1:].strip())

        # Explicit AI wake-up triggers
        ais_match = self._WAKE_PREFIX_RE.match(raw)
        if ais_match:
            query = ais_match.group(1).strip() or raw
            return ("ai", query)

        if self._CONVERSATIONAL_WAKE_RE.match(raw):
            return ("ai", raw)

        if raw.startswith("?"):
            query = raw[1:].strip() or raw
            return ("ai", query)

        # Shell command detection
        tokens = raw.split()
        first_token = tokens[0].lower()

        if first_token in ("cd", "export", "unset", "pwd", "echo", "alias", "unalias", "source", "."):
            return ("shell", raw)

        if not raw.endswith("?"):
            if first_token in self._DIRECT_SHELL_COMMANDS:
                return ("shell", raw)
            if shutil.which(first_token) and (
                len(tokens) == 1
                or any(t.startswith(("-", "/", "./", "~/")) for t in tokens[1:])
                or any(op in raw for op in ("|", ">", "<", "&&", "||", ";"))
            ):
                return ("shell", raw)

        return ("ai", raw)

    def dispatch_input(self, user_input: str) -> None:
        """Dispatch user input to shell executor or stream renderer."""
        raw = user_input.strip()
        if not raw:
            return

        # Check for meta commands first
        first_token = raw.split()[0].lower()
        if (
            raw.startswith(":")
            or raw.startswith("/")
            or first_token in ("exit", "quit", "help", "clear", "provider", "model", "context")
        ):
            if self.handle_meta_command(raw):
                raise EOFError()
            return

        mode, payload = self._classify_input(raw)
        if mode == "shell":
            self._execute_with_remediation(payload)
            return

        # Natural language query - Stream tokens from active AI provider
        raw = payload
        self.is_streaming = True
        accumulated_tokens = []
        try:
            import asyncio
            from aishell.context.inspector import inspect_system_context
            from aishell.context.sanitizer import format_system_observation
            from aishell.providers.errors import ProviderError
            from aishell.providers.prompts import SYSTEM_PROMPT_CHAT

            # Record user query in multi-turn conversation memory per D-04, CONF-03
            self.conversation.add_user_message(raw)

            context_info = inspect_system_context(cwd=os.getcwd())
            observation = format_system_observation(context_info)
            system_instruction = f"{SYSTEM_PROMPT_CHAT}\n\n{observation}"

            # Retrieve active multi-turn conversation history structured for LLM
            messages = self.conversation.get_messages_for_llm(system_instruction)

            def _token_generator():
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                agen = self.provider.stream_chat(messages, system_prompt=system_instruction)
                try:
                    while True:
                        try:
                            token = loop.run_until_complete(agen.__anext__())
                            accumulated_tokens.append(token)
                            yield token
                        except StopAsyncIteration:
                            break
                finally:
                    try:
                        loop.run_until_complete(agen.aclose())
                    except Exception:
                        pass

            self.renderer.stream_markdown(_token_generator())

            # Record assistant response in conversation memory
            full_text = "".join(accumulated_tokens)
            if full_text.strip():
                self.conversation.add_assistant_message(full_text)

            # Safety Gate: check if response proposed a shell command per EXEC-02, D-05
            from aishell.providers.schema import extract_proposal_from_text

            proposal = extract_proposal_from_text(full_text)
            if proposal and proposal.command.strip():
                approved_cmd = self.safety_gate.process_proposal(
                    proposal=proposal,
                    console=self.console,
                    prompt_session=self.session,
                )
                if approved_cmd:
                    self._execute_with_remediation(approved_cmd)
                    last_exec = getattr(self, "_last_execution", None)
                    if last_exec:
                        _, exec_code, exec_output = last_exec
                        from aishell.context.privacy import PrivacyGuard
                        redacted_out = PrivacyGuard().redact(exec_output or "")
                        if len(redacted_out) > 4000:
                            redacted_out = redacted_out[:4000] + "\n...[truncated]..."
                        self.conversation.add_user_message(
                            f'<command_output command="{approved_cmd}" exit_code="{exec_code}" untrusted="true">\n'
                            f"{redacted_out}\n"
                            "</command_output>"
                        )
                        self.console.print(
                            f"[dim]✓ Command finished (exit {exec_code}). Output saved to AI context — type 'ais continue' or ask a follow-up.[/dim]"
                        )

        except KeyboardInterrupt:
            # If tokens were streamed before interruption, save partial response in memory
            if accumulated_tokens:
                partial_text = "".join(accumulated_tokens)
                if partial_text.strip():
                    self.conversation.add_assistant_message(partial_text)
            # Re-raise so run() handles generation cancellation without session death
            raise
        except ProviderError as err:
            guidance_text = f"\n\n[bold yellow]Guidance:[/bold yellow] {err.guidance}" if err.guidance else ""
            self.renderer.render_error(f"{err.message}{guidance_text}")
        except Exception as exc:
            self.renderer.render_error(f"Generation error: {exc}")
        finally:
            self.is_streaming = False

    def _cleanup_async_loop(self) -> None:
        """Safely shut down provider clients, async generators, and pending tasks."""
        try:
            import asyncio
            import gc

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                return

            if not loop.is_closed():
                if hasattr(self, "provider") and hasattr(self.provider, "aclose"):
                    try:
                        loop.run_until_complete(self.provider.aclose())
                    except Exception:
                        pass

                gc.collect()
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception:
                    pass

                try:
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except Exception:
                    pass

                try:
                    loop.close()
                except Exception:
                    pass
        except Exception:
            pass

    def run(self) -> None:
        """Run interactive REPL event loop."""
        render_banner(self.console, self.settings)

        try:
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
                        self.console.print("\n[dim cyan]Goodbye![/dim cyan]")
                        break
                    else:
                        self.last_interrupt_time = now
                        self.console.print("\n[dim](Press Ctrl+C again or type :exit to quit)[/dim]")
                        continue

                except EOFError:
                    self.console.print("[dim cyan]Goodbye![/dim cyan]")
                    break
                except Exception as exc:
                    self.renderer.render_error(f"Unexpected error: {exc}")
        finally:
            self._cleanup_async_loop()
