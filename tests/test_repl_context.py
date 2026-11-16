"""Unit tests for REPL /context command and provider prompt injection."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from rich.console import Console
from typer.testing import CliRunner

from aishell.cli import app, execute_one_shot
from aishell.ui.repl import InteractiveREPL

runner = CliRunner()


def test_repl_context_meta_command():
    """Verify /context in REPL displays context table without terminating session."""
    test_console = Console(file=MagicMock())
    repl = InteractiveREPL(console=test_console)

    with patch("aishell.context.display.render_context_table") as mock_render:
        # Should return False (does not terminate session)
        assert repl.handle_meta_command("/context") is False
        mock_render.assert_called_once()


def test_repl_query_injects_system_observation():
    """Verify natural language query in REPL passes system_observation into provider."""
    test_console = Console(file=MagicMock())
    mock_provider = MagicMock()
    mock_provider.name = "mock"
    mock_provider.model = "mock-model"

    captured_prompt = None

    async def fake_stream(_messages, system_prompt=None):
        nonlocal captured_prompt
        captured_prompt = system_prompt
        yield "response token"

    mock_provider.stream_chat = fake_stream

    repl = InteractiveREPL(console=test_console, provider=mock_provider)
    repl.dispatch_input("how do I check open ports?")

    assert captured_prompt is not None
    assert '<system_observation untrusted="true">' in captured_prompt
    assert "</system_observation>" in captured_prompt


def test_oneshot_query_injects_system_observation():
    """Verify execute_one_shot passes system_observation into provider stream."""
    mock_provider = MagicMock()
    mock_provider.name = "mock"
    mock_provider.model = "mock-model"

    captured_prompt = None

    async def fake_stream(_messages, system_prompt=None):
        nonlocal captured_prompt
        captured_prompt = system_prompt
        yield "one-shot token"

    mock_provider.stream_chat = fake_stream

    with patch("aishell.providers.factory.get_provider", return_value=mock_provider):
        execute_one_shot(query="list systemctl services")

    assert captured_prompt is not None
    assert '<system_observation untrusted="true">' in captured_prompt
    assert "</system_observation>" in captured_prompt

