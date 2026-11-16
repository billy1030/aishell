"""Command Line Interface for aishell."""

import os
import sys
import time
import uuid
from typing import Optional
import typer
from rich.console import Console
from typer.core import TyperGroup

from aishell.config.settings import get_settings
from aishell.execution.builtins import sync_compound_cwd, try_execute_builtin
from aishell.execution.pty_runner import run_in_pty
from aishell.storage.history import HistoryManager
from aishell.ui.renderer import RichStreamRenderer

MAX_STDIN_BYTES = 512 * 1024  # 512KB bound per T-02-01


class DefaultCommandGroup(TyperGroup):
    """Custom TyperGroup that routes unrecognised non-option arguments to the ask command."""

    def resolve_command(self, ctx, args):
        cmd_name = args[0] if args else None
        if cmd_name and cmd_name not in self.commands and not cmd_name.startswith("-"):
            # Prepend default 'ask' command for bare positional queries per D-08
            return super().resolve_command(ctx, ["ask"] + args)
        return super().resolve_command(ctx, args)


app = typer.Typer(
    cls=DefaultCommandGroup,
    name="aishell",
    help="Terminal AI Shell - Interactive, system-aware Linux AI console assistant and REPL",
    no_args_is_help=False,
)
console = Console()
_SESSION_ID = str(uuid.uuid4())[:8]


def read_piped_stdin() -> Optional[str]:
    """Read piped stdin if available, capped to 512KB per T-02-01."""
    try:
        if sys.stdin and hasattr(sys.stdin, "isatty") and not sys.stdin.isatty():
            raw_text = sys.stdin.read(MAX_STDIN_BYTES + 1024)
            if not raw_text:
                return None
            raw_bytes = raw_text.encode("utf-8", errors="replace")
            if len(raw_bytes) > MAX_STDIN_BYTES:
                console.print(
                    "[bold yellow]Warning:[/bold yellow] Piped stdin exceeds 512KB and was truncated.",
                    style="yellow",
                )
                return raw_bytes[:MAX_STDIN_BYTES].decode("utf-8", errors="replace")
            return raw_text
    except Exception:
        pass
    return None


def execute_pipeline(command: str, session_id: Optional[str] = None) -> int:
    """Core execution pipeline coordinating builtins, PTY runner, and audit logging."""
    settings = get_settings()
    history = HistoryManager(
        db_path=settings.storage.history_db_path,
        max_records=settings.storage.max_history_records,
    )
    sess_id = session_id or _SESSION_ID
    current_cwd = os.getcwd()

    # Step 1: Check and intercept shell builtins (cd, export, unset) per D-05
    start_time = time.perf_counter()
    builtin_result = try_execute_builtin(command)

    if builtin_result is not None:
        exit_code, output = builtin_result
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        if output:
            console.print(output)

        history.record_execution(
            session_id=sess_id,
            command=command,
            cwd=current_cwd,
            exit_code=exit_code,
            duration_ms=duration_ms,
            output=output,
            executed_by="user",
        )
        return exit_code

    # Step 2: Dispatch external command to managed PTY runner per D-01, EXEC-04
    result = run_in_pty(
        command=command,
        cwd=current_cwd,
        timeout=float(settings.execution.timeout_seconds),
        echo_to_terminal=True,
    )

    # Step 3: Synchronize compound cwd if command contained cd per D-06
    sync_compound_cwd(command, exit_code=result.exit_code)

    # Step 4: Record execution audit record in SQLite history database per D-09, EXEC-06
    history.record_execution(
        session_id=sess_id,
        command=command,
        cwd=current_cwd,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        output=result.output,
        executed_by="user",
    )

    return result.exit_code


def execute_one_shot(query: Optional[str] = None, piped_stdin: Optional[str] = None) -> None:
    """Execute a one-shot query via RichStreamRenderer per REPL-05, D-08, D-09."""
    parts = []
    if piped_stdin:
        parts.append(piped_stdin.strip())
    if query:
        parts.append(query.strip())

    combined_input = "\n\n".join(parts)
    if not combined_input:
        return

    renderer = RichStreamRenderer()
    # Live streaming output render (In Phase 3 this dispatches to LLM provider)
    tokens = [combined_input]
    renderer.stream_markdown(tokens)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    command: Optional[str] = typer.Option(
        None,
        "-c",
        "--command",
        help="Execute a one-shot AI query without entering REPL",
    ),
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Show aishell version"
    ),
) -> None:
    """Main aishell entrypoint."""
    if version:
        from aishell import __version__

        console.print(f"[bold cyan]aishell[/bold cyan] version [green]{__version__}[/green]")
        raise typer.Exit(code=0)

    # Check for piped stdin once and stash in ctx.obj
    ctx.ensure_object(dict)
    piped_stdin = read_piped_stdin()
    ctx.obj["piped_stdin"] = piped_stdin

    if ctx.invoked_subcommand is None:
        if command or piped_stdin:
            execute_one_shot(query=command, piped_stdin=piped_stdin)
            raise typer.Exit(code=0)

        # Bare aishell launches REPL (Wired in Phase 2 Plan 03)
        console.print("[dim]Interactive REPL will be launched here (Phase 2). Use 'aishell exec <cmd>' for command execution.[/dim]")


@app.command(name="ask", hidden=True)
def ask_cmd(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Natural language query for one-shot execution"),
) -> None:
    """Execute a bare positional one-shot query."""
    piped_stdin = (ctx.obj or {}).get("piped_stdin") if ctx.obj else None
    execute_one_shot(query=query, piped_stdin=piped_stdin)


@app.command(name="exec")
def exec_cmd(
    command: str = typer.Argument(..., help="Shell command string to execute"),
) -> None:
    """Execute a shell command with real-time output and exit code return (Tracer)."""
    exit_code = execute_pipeline(command)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@app.command(name="run")
def run_cmd(
    command: str = typer.Argument(..., help="Shell command string to execute"),
) -> None:
    """Alias for exec command."""
    exit_code = execute_pipeline(command)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
