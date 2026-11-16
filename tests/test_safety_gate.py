"""Unit tests for interactive confirmation gate and SafetyGate service per D-03, D-04, D-05."""

import io
from unittest.mock import patch
from rich.console import Console
from aishell.providers.schema import CommandProposal
from aishell.safety.gate import (
    GateAction,
    SafetyGate,
    prompt_confirmation,
    prompt_edit_command,
)


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


def test_prompt_edit_command_success():
    """Verify prompt_edit_command returns modified string."""
    output = io.StringIO()
    console = Console(file=output, force_terminal=False)
    edited = prompt_edit_command(
        initial_command="ls",
        console=console,
        input_fn=lambda initial: "ls -lah /tmp",
    )
    assert edited == "ls -lah /tmp"


def test_prompt_edit_command_cancel():
    """Verify prompt_edit_command returns None on empty or interrupted input."""
    output = io.StringIO()
    console = Console(file=output, force_terminal=False)
    # Empty string
    assert (
        prompt_edit_command(
            initial_command="ls",
            console=console,
            input_fn=lambda initial: "",
        )
        is None
    )
    # KeyboardInterrupt
    def _raise_interrupt(initial):
        raise KeyboardInterrupt()

    assert (
        prompt_edit_command(
            initial_command="ls",
            console=console,
            input_fn=_raise_interrupt,
        )
        is None
    )


def test_safety_gate_service_confirm():
    """Verify SafetyGate returns approved command on explicit confirmation."""
    gate = SafetyGate()
    proposal = _make_proposal("ls -la")
    output = io.StringIO()
    console = Console(file=output, force_terminal=False)

    cmd = gate.process_proposal(
        proposal=proposal,
        console=console,
        input_fn=lambda prompt: "y",
    )
    assert cmd == "ls -la"


def test_safety_gate_service_cancel():
    """Verify SafetyGate returns None on cancellation."""
    gate = SafetyGate()
    proposal = _make_proposal("ls -la")
    output = io.StringIO()
    console = Console(file=output, force_terminal=False)

    cmd = gate.process_proposal(
        proposal=proposal,
        console=console,
        input_fn=lambda prompt: "n",
    )
    assert cmd is None


def test_safety_gate_service_edit_and_confirm():
    """Verify SafetyGate supports editing a command, re-presenting it, and confirming."""
    gate = SafetyGate()
    proposal = _make_proposal("touch test.txt")
    output = io.StringIO()
    console = Console(file=output, force_terminal=False)

    responses = ["e", "y"]  # First prompt: edit; second prompt: confirm

    def _mock_input(prompt):
        return responses.pop(0)

    def _mock_edit(initial):
        return "touch test_edited.txt"

    cmd = gate.process_proposal(
        proposal=proposal,
        console=console,
        input_fn=_mock_input,
        edit_fn=_mock_edit,
    )
    assert cmd == "touch test_edited.txt"
    rendered = output.getvalue()
    assert "touch test.txt" in rendered
    assert "touch test_edited.txt" in rendered
