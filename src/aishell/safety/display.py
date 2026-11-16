"""Proposal Card Rich presentation and visual risk badges per D-02 and EXEC-01."""

from typing import Optional
from rich.console import Console, Group
from rich.markup import escape
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from aishell.providers.schema import CommandProposal
from aishell.safety.classifier import RiskLevel, classify_risk


def get_risk_badge(risk_tier: str) -> Text:
    """Return a styled Rich Text badge for a risk tier."""
    norm = risk_tier.lower()
    if norm == RiskLevel.SAFE.value:
        return Text.from_markup("[bold green][SAFE][/bold green]")
    elif norm == RiskLevel.MUTATING.value:
        return Text.from_markup("[bold yellow][MUTATING][/bold yellow]")
    elif norm == RiskLevel.HIGH_RISK.value:
        return Text.from_markup("[bold white on red][HIGH-RISK][/bold white on red]")
    else:
        return Text.from_markup(f"[bold yellow][{escape(norm.upper())}][/bold yellow]")


def render_proposal(
    proposal: CommandProposal,
    console: Optional[Console] = None,
) -> Panel:
    """Render a structured Proposal Card with visual risk badges and syntax highlighting.

    Displays:
      - Header with risk badge and purpose
      - Syntax-highlighted bash command
      - Explanation of flags, parameters, and mechanics
      - Sudo privilege warnings and high-risk caution banners
    """
    # Reconcile proposal risk_tier with deterministic heuristics per D-01
    effective_risk = classify_risk(proposal.command, model_risk=proposal.risk_tier)

    # Determine border and badge styling
    badge = get_risk_badge(effective_risk.value)
    if effective_risk == RiskLevel.SAFE:
        border_style = "green"
    elif effective_risk == RiskLevel.MUTATING:
        border_style = "yellow"
    else:
        border_style = "red"

    # Build title
    title_text = Text()
    title_text.append_text(badge)
    title_text.append(" ")
    title_text.append(proposal.purpose or "Proposed Shell Command", style="bold")

    elements = []

    # High-risk warning notice per D-02
    if effective_risk == RiskLevel.HIGH_RISK:
        caution_text = Text.from_markup(
            "[bold red]CAUTION: High-risk command with potential system-wide impact[/bold red]"
        )
        elements.append(caution_text)
        elements.append(Text(""))

    # Command syntax box
    syntax = Syntax(
        proposal.command,
        "bash",
        theme="monokai",
        background_color="default",
        word_wrap=True,
    )
    elements.append(syntax)

    # Explanation section
    if proposal.explanation:
        elements.append(Text(""))
        expl_text = Text.from_markup(f"[dim]{escape(proposal.explanation.strip())}[/dim]")
        elements.append(expl_text)

    # Sudo indicator
    if proposal.requires_sudo or proposal.command.strip().startswith("sudo"):
        elements.append(Text(""))
        sudo_notice = Text.from_markup(
            "[bold red]• Requires sudo / administrative privileges[/bold red]"
        )
        elements.append(sudo_notice)

    # Remediation indicator
    if proposal.remediation:
        elements.append(Text(""))
        elements.append(Text.from_markup("[bold cyan]• Remediation for prior command failure[/bold cyan]"))

    panel = Panel(
        Group(*elements),
        title=title_text,
        title_align="left",
        border_style=border_style,
        padding=(1, 2),
    )

    if console:
        console.print(panel)

    return panel

