"""Rich terminal UI display for inspected system context and sanitized environment variables."""

from typing import Optional
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from aishell.context.schema import SystemContext


def render_context_table(context: SystemContext, console: Optional[Console] = None) -> None:
    """Render a clean, styled Rich display of discovered host facts and sanitized env vars per D-04."""
    out = console or Console()

    # Host facts table
    facts_table = Table(show_header=True, header_style="bold cyan", expand=True)
    facts_table.add_column("Property", style="bold", width=22)
    facts_table.add_column("Value")

    facts_table.add_row("OS Distribution", f"{context.os_name} ({context.os_family} {context.os_version})")
    facts_table.add_row("Kernel & Arch", f"{context.kernel} ({context.arch})")
    privilege_badge = "[bold red]root (privileged)[/bold red]" if context.is_root else "[green]standard (unprivileged)[/green]"
    facts_table.add_row("User & Privileges", f"{context.user} [{privilege_badge}]")
    facts_table.add_row("Working Directory", context.cwd)
    facts_table.add_row("Active Shell", context.shell)
    facts_table.add_row("Package Manager", f"[cyan]{context.package_manager}[/cyan]")

    if context.git_branch:
        status_text = "[green]clean[/green]" if context.git_clean else "[yellow]dirty (uncommitted changes)[/yellow]"
        facts_table.add_row("Git Repository", f"branch [bold magenta]{context.git_branch}[/bold magenta] ({status_text})")
    else:
        facts_table.add_row("Git Repository", "[dim]not a git repository[/dim]")

    # Sanitized environment variables table
    env_table = Table(show_header=True, header_style="bold cyan", expand=True)
    env_table.add_column("Variable", style="bold green", width=22)
    env_table.add_column("Sanitized Value")

    if context.env_vars:
        for k, v in sorted(context.env_vars.items()):
            env_table.add_row(k, v)
    else:
        env_table.add_row("[dim]None[/dim]", "[dim]No allowlisted environment variables detected[/dim]")

    group = Group(
        Panel(facts_table, title="[bold]Host System Facts[/bold]", border_style="cyan"),
        Panel(env_table, title="[bold]Sanitized Environment Variables (Allowlisted)[/bold]", border_style="green"),
    )

    out.print(Panel(group, title="[bold cyan]aishell System Context & Privacy Guard[/bold cyan]", border_style="blue"))

