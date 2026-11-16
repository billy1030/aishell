"""Unit and integration tests for CLI provider flags, one-shot streaming, and error guidance."""

from unittest.mock import AsyncMock, MagicMock, patch
from typer.testing import CliRunner

from aishell.cli import app
from aishell.providers.errors import AuthenticationError, ConnectionError

runner = CliRunner()


def test_cli_oneshot_provider_streaming_success():
    """Verify -c with -p streams tokens through the specified provider."""
    mock_provider = MagicMock()
    mock_provider.name = "gemini"
    mock_provider.model = "gemini-2.0-flash"

    async def fake_stream(_messages):
        yield "To list files, use: "
        yield "`ls -la`"

    mock_provider.stream_chat = fake_stream

    with patch("aishell.providers.factory.get_provider", return_value=mock_provider) as mock_get_p:
        result = runner.invoke(app, ["-c", "how do I list files?", "-p", "gemini", "-m", "gemini-2.0-flash"])
        assert result.exit_code == 0
        assert "To list files, use" in result.output
        mock_get_p.assert_called_once()
        assert mock_get_p.call_args[1]["name"] == "gemini"
        assert mock_get_p.call_args[1]["model"] == "gemini-2.0-flash"


def test_cli_oneshot_auth_error_displays_guidance():
    """Verify missing credentials produces clean error guidance without raw stack traces."""
    with patch(
        "aishell.providers.factory.get_provider",
        side_effect=AuthenticationError("openai"),
    ):
        result = runner.invoke(app, ["-c", "find large files", "-p", "openai"])
        assert result.exit_code == 1
        assert "Authentication failed for provider 'openai'" in result.output
        assert "Guidance:" in result.output
        assert "OPENAI_API_KEY" in result.output
        assert "export" in result.output
        # Verify no unhandled traceback was printed
        assert "Traceback (most recent call last)" not in result.output


def test_cli_oneshot_connection_error_displays_guidance():
    """Verify daemon connection failure prints actionable guidance (e.g. ollama serve)."""
    with patch(
        "aishell.providers.factory.get_provider",
        side_effect=ConnectionError("ollama", url="http://localhost:11434"),
    ):
        result = runner.invoke(app, ["-c", "check system load", "-p", "ollama"])
        assert result.exit_code == 1
        assert "Could not connect to ollama" in result.output
        assert "ollama serve" in result.output
        assert "Traceback (most recent call last)" not in result.output
