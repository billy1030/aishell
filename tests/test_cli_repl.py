"""Tests for CLI REPL invocation and terminal fallback."""

from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from aishell.cli import app

runner = CliRunner()


def test_cli_bare_interactive_tty_launches_repl():
    """Verify bare aishell in a TTY launches InteractiveREPL.run()."""
    mock_repl_instance = MagicMock()

    with patch("aishell.cli.is_interactive_terminal", return_value=True):
        with patch("aishell.ui.repl.InteractiveREPL", return_value=mock_repl_instance) as mock_repl_cls:
            result = runner.invoke(app, [])
            assert result.exit_code == 0
            mock_repl_cls.assert_called_once()
            mock_repl_instance.run.assert_called_once()


def test_cli_bare_non_tty_shows_usage_message():
    """Verify bare aishell without a TTY displays helpful usage information."""
    with patch("aishell.cli.is_interactive_terminal", return_value=False):
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "no command or query provided" in result.output
        assert "cat file | aishell" in result.output


def test_cli_bare_interactive_handles_signals_cleanly():
    """Verify clean exit when InteractiveREPL.run() raises KeyboardInterrupt or EOFError."""
    mock_repl_instance = MagicMock()
    mock_repl_instance.run.side_effect = KeyboardInterrupt()

    with patch("aishell.cli.is_interactive_terminal", return_value=True):
        with patch("aishell.ui.repl.InteractiveREPL", return_value=mock_repl_instance):
            result = runner.invoke(app, [])
            assert result.exit_code == 0
