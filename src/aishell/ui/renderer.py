"""Terminal UI rendering engine using Rich.

Provides streaming markdown rendering, transient status spinners, terminal
capability detection, and safe degradation for non-TTY or dumb terminals per REPL-03, D-05, D-06, D-07.
"""

import os
import re
import sys
from contextlib import contextmanager
from typing import Any, Dict, Generator, Iterable, Optional
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.status import Status
from rich.text import Text


def detect_terminal_capabilities() -> Dict[str, Any]:
    """Detect terminal capabilities including TTY status and color support.

    Adheres to NO_COLOR and TERM=dumb standards per D-07.
    """
    is_tty = bool(sys.stdout and hasattr(sys.stdout, "isatty") and sys.stdout.isatty())

    # Respect NO_COLOR standard (https://no-color.org)
    if "NO_COLOR" in os.environ and os.environ["NO_COLOR"].strip() != "":
        return {"is_tty": is_tty, "color_system": None, "interactive": is_tty}

    term = os.environ.get("TERM", "").lower()
    if term == "dumb":
        return {"is_tty": is_tty, "color_system": None, "interactive": False}

    colorterm = os.environ.get("COLORTERM", "").lower()
    if colorterm in ("truecolor", "24bit"):
        color_system = "truecolor"
    elif "256color" in term:
        color_system = "256"
    elif is_tty:
        color_system = "auto"
    else:
        color_system = None

    return {
        "is_tty": is_tty,
        "color_system": color_system,
        "interactive": is_tty and term != "dumb",
    }


def _condense_thinking(text: str) -> str:
    """Condense <think>...</think> blocks to at most 2 lines while streaming, and hide once complete."""
    if "<think>" not in text:
        return text

    # Strip any completed <think>...</think> blocks
    cleaned = re.sub(r"<think>[\s\S]*?</think>\s*", "", text)

    # If an unclosed <think> block is still streaming, show only its last 2 non-empty lines
    if "<think>" in cleaned:
        before, _, thinking_part = cleaned.partition("<think>")
        lines = [ln.strip() for ln in thinking_part.splitlines() if ln.strip()]
        tail = lines[-2:] if lines else ["..."]
        preview = "\n".join(f"> {ln[:100]}" for ln in tail)
        return f"{before}*Thinking...*\n{preview}".strip()

    return cleaned


class RichStreamRenderer:
    """Renders streaming Markdown and transient spinners to the terminal."""

    def __init__(
        self,
        console: Optional[Console] = None,
        stderr_console: Optional[Console] = None,
    ) -> None:
        self.caps = detect_terminal_capabilities()
        if console is not None:
            self.console = console
            # If explicit console passed, use its terminal status for interactivity
            self.interactive = bool(getattr(console, "is_terminal", self.caps["interactive"]))
        else:
            self.console = Console(
                color_system=self.caps["color_system"],
                highlight=False,
                legacy_windows=False if os.name == "nt" else None,
            )
            self.interactive = self.caps["interactive"]

        self.stderr_console = stderr_console or Console(stderr=True)

    @contextmanager
    def thinking_spinner(self, message: str = "Thinking...") -> Generator[Optional[Status], None, None]:
        """Display a transient status spinner that clears cleanly when finished per D-06."""
        if not self.interactive:
            yield None
            return

        status = self.console.status(f"[dim cyan]{message}[/dim cyan]", spinner="dots")
        status.start()
        try:
            yield status
        finally:
            status.stop()

    def stream_markdown(
        self,
        token_stream: Iterable[str],
        code_theme: str = "monokai",
    ) -> str:
        """Stream markdown tokens live using Rich Live display per D-05.

        Renders Markdown with Pygments syntax highlighting on code blocks.
        Falls back to plain text printing if output is not an interactive TTY.
        Returns the accumulated full response string.
        """
        accumulated_text = ""

        # Non-interactive fallback (pipes, redirects, dumb terminals)
        if not self.interactive:
            for token in token_stream:
                accumulated_text += token
                if hasattr(self.console, "file") and self.console.file:
                    self.console.file.write(token)
                    self.console.file.flush()
                else:
                    sys.stdout.write(token)
                    sys.stdout.flush()
            if hasattr(self.console, "file") and self.console.file:
                self.console.file.write("\n")
                self.console.file.flush()
            else:
                sys.stdout.write("\n")
                sys.stdout.flush()
            return accumulated_text

        # Interactive streaming via Rich Live: show Thinking spinner until first token arrives
        with Live(
            Spinner("dots", text="[dim cyan]Thinking...[/dim cyan]"),
            console=self.console,
            refresh_per_second=15,
            transient=False,
        ) as live:
            try:
                for token in token_stream:
                    accumulated_text += token
                    display_text = _condense_thinking(accumulated_text)
                    if display_text:
                        live.update(Markdown(display_text, code_theme=code_theme))
            finally:
                if not accumulated_text:
                    live.update(Text(""))

        return accumulated_text

    def render_markdown(self, text: str, code_theme: str = "monokai") -> None:
        """Render a complete Markdown document to the console."""
        md = Markdown(text, code_theme=code_theme)
        self.console.print(md)

    def render_error(self, message: str) -> None:
        """Render an error message formatted with red styling."""
        self.stderr_console.print(f"[bold red]Error:[/bold red] {message}")
