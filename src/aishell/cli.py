"""Command Line Interface for aishell."""

import subprocess
import sys
from typing import Optional
import typer
from rich.console import Console

app = typer.Typer(
    name="aishell",
    help="Terminal AI Shell - Interactive, system-aware Linux AI console assistant and REPL",
    no_args_is_help=False,
)
console = Console()


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


@app.command(name="exec")
def exec_cmd(
    command: str = typer.Argument(..., help="Shell command string to execute"),
) -> None:
    """Execute a shell command with real-time output and exit code return (Tracer)."""
    try:
        proc = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=False,
        )
        if proc.returncode != 0:
            raise typer.Exit(code=proc.returncode)
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[bold red]Execution error:[/bold red] {exc}", file=sys.stderr)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

