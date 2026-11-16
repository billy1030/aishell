"""Unit tests for Proposal Card presentation and visual risk badges per D-02 and EXEC-01."""

import io
from rich.console import Console
from aishell.providers.schema import CommandProposal
from aishell.safety.display import get_risk_badge, render_proposal


def test_get_risk_badge():
    """Verify risk badge generation returns styled text matching each tier."""
    safe_badge = get_risk_badge("safe")
    assert "[SAFE]" in safe_badge.plain

    mutating_badge = get_risk_badge("mutating")
    assert "[MUTATING]" in mutating_badge.plain

    high_risk_badge = get_risk_badge("high_risk")
    assert "[HIGH-RISK]" in high_risk_badge.plain


def test_render_proposal_safe():
    """Verify render_proposal formats a safe command properly."""
    proposal = CommandProposal(
        command="ls -la /var/log",
        purpose="List directory contents with detailed permissions",
        explanation="Uses -l for long format and -a to include hidden files",
        risk_tier="safe",
        requires_sudo=False,
    )

    output = io.StringIO()
    console = Console(file=output, force_terminal=False, width=100)
    panel = render_proposal(proposal, console=console)

    rendered = output.getvalue()
    assert "[SAFE]" in rendered
    assert "List directory contents" in rendered
    assert "ls -la /var/log" in rendered
    assert "Uses -l for long format" in rendered
    assert panel.border_style == "green"


def test_render_proposal_mutating():
    """Verify render_proposal formats a mutating command properly."""
    proposal = CommandProposal(
        command="touch testfile.txt",
        purpose="Create an empty file",
        explanation="Updates the access and modification times",
        risk_tier="mutating",
        requires_sudo=False,
    )

    output = io.StringIO()
    console = Console(file=output, force_terminal=False, width=100)
    panel = render_proposal(proposal, console=console)

    rendered = output.getvalue()
    assert "[MUTATING]" in rendered
    assert "Create an empty file" in rendered
    assert "touch testfile.txt" in rendered
    assert panel.border_style == "yellow"


def test_render_proposal_high_risk():
    """Verify render_proposal formats a high-risk command with red styling and caution notice."""
    proposal = CommandProposal(
        command="rm -rf /tmp/testdir",
        purpose="Recursively remove directory",
        explanation="Deletes directory and all contents forcefully",
        risk_tier="high_risk",
        requires_sudo=True,
    )

    output = io.StringIO()
    console = Console(file=output, force_terminal=False, width=100)
    panel = render_proposal(proposal, console=console)

    rendered = output.getvalue()
    assert "[HIGH-RISK]" in rendered
    assert "CAUTION: High-risk command" in rendered
    assert "Requires sudo / administrative privileges" in rendered
    assert "rm -rf /tmp/testdir" in rendered
    assert panel.border_style == "red"


def test_render_proposal_reconciles_hallucinated_model_risk():
    """Verify render_proposal automatically upgrades a high-risk command even if model labeled it safe."""
    proposal = CommandProposal(
        command="rm -rf /",
        purpose="Clean up system",
        explanation="Cleans disk space",
        risk_tier="safe",  # Model hallucinated 'safe'!
    )

    output = io.StringIO()
    console = Console(file=output, force_terminal=False, width=100)
    panel = render_proposal(proposal, console=console)

    rendered = output.getvalue()
    assert "[HIGH-RISK]" in rendered
    assert "CAUTION: High-risk command" in rendered
    assert panel.border_style == "red"

