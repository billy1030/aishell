"""Integration tests for CLI one-shot execution with SafetyGate per EXEC-02, EXEC-03."""

from unittest.mock import MagicMock, patch
import pytest
from typer.testing import CliRunner
from aishell.cli import app
from aishell.safety.gate import GateAction

runner = CliRunner()


@pytest.fixture
def mock_proposal_provider(monkeypatch):
    """Mock provider yielding a structured CommandProposal JSON block."""
    mock_p = MagicMock()
    mock_p.name = "mock"
    mock_p.model = "mock-model"

    proposal_json = (
        '```json\n{\n  "command": "echo \\"confirmed execution\\"",\n'
        '  "purpose": "Test command execution",\n'
        '  "explanation": "Prints confirmed message",\n'
        '  "risk_tier": "safe",\n'
        '  "requires_sudo": false\n}\n```'
    )

    async def fake_stream(messages, *args, **kwargs):
        yield proposal_json

    mock_p.stream_chat = fake_stream
    monkeypatch.setattr("aishell.providers.factory.get_provider", lambda **kwargs: mock_p)
    return mock_p


def test_cli_oneshot_safety_gate_confirmed(mock_proposal_provider, monkeypatch):
    """Verify operator pressing 'y' confirms and executes proposed command."""
    mock_pipeline = MagicMock(return_value=0)
    monkeypatch.setattr("aishell.cli.execute_pipeline", mock_pipeline)

    # Mock SafetyGate.process_proposal to simulate operator confirmation
    with patch("aishell.safety.gate.SafetyGate.process_proposal", return_value="echo \"confirmed execution\"") as mock_gate:
        result = runner.invoke(app, ["-c", "run test command"])
        assert result.exit_code == 0
        mock_gate.assert_called_once()
        mock_pipeline.assert_called_once_with('echo "confirmed execution"')


def test_cli_oneshot_safety_gate_cancelled(mock_proposal_provider, monkeypatch):
    """Verify operator pressing 'n' cancels execution without invoking pipeline."""
    mock_pipeline = MagicMock(return_value=0)
    monkeypatch.setattr("aishell.cli.execute_pipeline", mock_pipeline)

    with patch("aishell.safety.gate.SafetyGate.process_proposal", return_value=None) as mock_gate:
        result = runner.invoke(app, ["-c", "run dangerous command"])
        assert result.exit_code == 0
        mock_gate.assert_called_once()
        mock_pipeline.assert_not_called()


def test_cli_oneshot_safety_gate_edited(mock_proposal_provider, monkeypatch):
    """Verify operator selecting 'e' edits command and executes modified string."""
    mock_pipeline = MagicMock(return_value=0)
    monkeypatch.setattr("aishell.cli.execute_pipeline", mock_pipeline)

    edited_cmd = 'echo "modified by operator"'
    with patch("aishell.safety.gate.SafetyGate.process_proposal", return_value=edited_cmd) as mock_gate:
        result = runner.invoke(app, ["-c", "run command and edit"])
        assert result.exit_code == 0
        mock_gate.assert_called_once()
        mock_pipeline.assert_called_once_with(edited_cmd)

