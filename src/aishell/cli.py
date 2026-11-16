"""Command Line Interface for aishell."""

import os
import sys
import time
import uuid
from typing import Optional
import typer
from rich.console import Console

from aishell.config.settings import get_settings
from aishell.execution.builtins import sync_compound_cwd, try_execute_builtin
from aishell.execution.pty_runner import run_in_pty
from aishell.storage.history import HistoryManager

app = typer.Typer(
    name="aishell",
    help="Terminal AI Shell - Interactive, system-aware Linux AI console assistant and REPL",
    no_args_is_help=False,
)
console = Console()
_SESSION_ID = str(uuid.uuid4())[:8]


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Show aishell version"
    ),
) -> None:
    """Main aishell entrypoint."""
    if version:
        from aishell import __version__

        console.print(f"[bold cyan]aishell[/bold cyan] version [green]{__version__}[/green]")
        raise typer.Exit(code=0)
    if ctx.invoked_subcommand is None:
        console.print("[dim]Interactive REPL will be launched here (Phase 2). Use 'aishell exec <cmd>' for command execution.[/dim]")


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
