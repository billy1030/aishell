"""Unit tests for interactive confirmation gate per D-03 and EXEC-02."""

import io
from unittest.mock import patch
from rich.console import Console
from aishell.providers.schema import CommandProposal
from aishell.safety.gate import GateAction, prompt_confirmation


def _make_proposal(command: str = "ls -la") -> CommandProposal:
    return CommandProposal(
        command=command,
        purpose="List directory",
        explanation="Read-only test command",
        risk_tier="safe",
    )


def test_prompt_confirmation_confirm_yes():
    """Verify entering 'y' or 'yes' confirms execution."""
    proposal = _make_proposal()
    output = io.StringIO()
    console = Console(file=output, force_terminal=False)

    for resp in ("y", "Y", "yes", "YES", "  y  "):
        action = prompt_confirmation(
            proposal=proposal,
            console=console,
            input_fn=lambda prompt, r=resp: r,
        )
        assert action == GateAction.CONFIRM


def test_prompt_confirmation_edit():
    """Verify entering 'e' or 'edit' requests inline editing."""
    proposal = _make_proposal()
    output = io.StringIO()
    console = Console(file=output, force_terminal=False)

    for resp in ("e", "E", "edit", "EDIT", "  e  "):
        action = prompt_confirmation(
            proposal=proposal,
            console=console,
            input_fn=lambda prompt, r=resp: r,
        )
        assert action == GateAction.EDIT


def test_prompt_confirmation_cancel_default_and_no():
    """Verify pressing Enter (empty), 'n', 'no', or unrecognized inputs cancel execution."""
    proposal = _make_proposal()

    for resp in ("", "   ", "n", "N", "no", "NO", "cancel", "q", "exit", "foo"):
        output = io.StringIO()
        console = Console(file=output, force_terminal=False)
        action = prompt_confirmation(
            proposal=proposal,
            console=console,
            input_fn=lambda prompt, r=resp: r,
        )
        assert action == GateAction.CANCEL
        assert "cancelled by operator" in output.getvalue()


def test_prompt_confirmation_interrupt_and_eof():
    """Verify Ctrl+C (KeyboardInterrupt) and Ctrl+D (EOFError) cancel cleanly."""
    proposal = _make_proposal()

    def _raise_interrupt(prompt):
        raise KeyboardInterrupt()

    output = io.StringIO()
    console = Console(file=output, force_terminal=False)
    action = prompt_confirmation(proposal=proposal, console=console, input_fn=_raise_interrupt)
    assert action == GateAction.CANCEL
    assert "cancelled by operator" in output.getvalue()

    def _raise_eof(prompt):
        raise EOFError()

    output = io.StringIO()
    console = Console(file=output, force_terminal=False)
    action = prompt_confirmation(proposal=proposal, console=console, input_fn=_raise_eof)
    assert action == GateAction.CANCEL
    assert "cancelled by operator" in output.getvalue()


def test_prompt_confirmation_non_interactive_guard():
    """Verify execution is blocked when standard input is not an interactive terminal."""
    proposal = _make_proposal()
    output = io.StringIO()
    console = Console(file=output, force_terminal=False)

    with patch("aishell.safety.gate.is_interactive_stdin", return_value=False):
        action = prompt_confirmation(proposal=proposal, console=console, input_fn=None)
        assert action == GateAction.CANCEL
        assert "Execution blocked" in output.getvalue()
