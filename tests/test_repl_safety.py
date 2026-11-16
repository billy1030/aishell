"""Integration tests for REPL session with SafetyGate per EXEC-02, EXEC-03, D-05."""

from unittest.mock import MagicMock, patch
import pytest
from rich.console import Console

from aishell.config.settings import AishellSettings
from aishell.ui.history import SQLiteHistory
from aishell.ui.repl import InteractiveREPL


@pytest.fixture
def repl_with_mock_provider(tmp_path):
    """Create an InteractiveREPL with an isolated history DB and mock provider."""
    db_file = tmp_path / "test_safety_repl.db"
    settings = AishellSettings()
    settings.storage.history_db_path = db_file
    console = Console(file=MagicMock(), force_terminal=False)
    history = SQLiteHistory(db_path=db_file, session_id="test-safety-sess")

    mock_provider = MagicMock()
    mock_provider.name = "mock"
    mock_provider.model = "mock-model"

    proposal_text = (
        '```json\n{\n  "command": "cat /var/log/syslog",\n'
        '  "purpose": "Inspect system logs",\n'
        '  "explanation": "Reads log file",\n'
        '  "risk_tier": "safe",\n'
        '  "requires_sudo": false\n}\n```'
    )

    async def fake_stream(messages, *args, **kwargs):
        yield proposal_text

    mock_provider.stream_chat = fake_stream

    repl = InteractiveREPL(
        settings=settings,
        console=console,
        history=history,
        provider=mock_provider,
    )

    return repl


def test_repl_natural_language_gate_confirmed(repl_with_mock_provider):
    """Verify REPL natural language query triggers SafetyGate and runs command when confirmed."""
    repl = repl_with_mock_provider
    mock_executor = MagicMock(return_value=0)
    repl.executor_fn = mock_executor

    with patch.object(repl.safety_gate, "process_proposal", return_value="cat /var/log/syslog") as mock_process:
        repl.dispatch_input("show me syslog")
        mock_process.assert_called_once()
        mock_executor.assert_called_once_with("cat /var/log/syslog")


def test_repl_natural_language_gate_cancelled(repl_with_mock_provider):
    """Verify REPL natural language query cancels without running command when aborted at gate."""
    repl = repl_with_mock_provider
    mock_executor = MagicMock(return_value=0)
    repl.executor_fn = mock_executor

    with patch.object(repl.safety_gate, "process_proposal", return_value=None) as mock_process:
        repl.dispatch_input("show me syslog")
        mock_process.assert_called_once()
        mock_executor.assert_not_called()


def test_repl_natural_language_gate_edited(repl_with_mock_provider):
    """Verify REPL natural language query executes edited command when modified in gate."""
    repl = repl_with_mock_provider
    mock_executor = MagicMock(return_value=0)
    repl.executor_fn = mock_executor

    edited_cmd = "cat /var/log/syslog | grep error"
    with patch.object(repl.safety_gate, "process_proposal", return_value=edited_cmd) as mock_process:
        repl.dispatch_input("show me syslog")
        mock_process.assert_called_once()
        mock_executor.assert_called_once_with(edited_cmd)


def test_repl_direct_shell_bypasses_proposal(repl_with_mock_provider):
    """Verify direct shell commands (e.g. !echo 123) run directly through executor without gate."""
    repl = repl_with_mock_provider
    mock_executor = MagicMock(return_value=0)
    repl.executor_fn = mock_executor

    with patch.object(repl.safety_gate, "process_proposal") as mock_process:
        repl.dispatch_input("!echo direct command")
        mock_process.assert_not_called()
        mock_executor.assert_called_once_with("echo direct command")
