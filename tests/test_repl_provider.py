"""Unit tests for InteractiveREPL provider streaming, runtime switching, and error handling."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from rich.console import Console

from aishell.config.settings import AishellSettings
from aishell.providers.errors import AuthenticationError
from aishell.ui.repl import InteractiveREPL


def test_repl_prompt_tokens():
    mock_provider = MagicMock()
    mock_provider.name = "gemini"
    mock_provider.model = "gemini-2.0-flash"

    repl = InteractiveREPL(provider=mock_provider)
    tokens = repl.get_prompt_tokens()
    token_texts = [t[1] for t in tokens]
    full_prompt = "".join(token_texts)
    assert full_prompt in ("aishell $ ", "aishell # ")


def test_repl_provider_meta_commands():
    test_console = Console(file=MagicMock())
    repl = InteractiveREPL(console=test_console)

    # Inspect active provider
    assert repl.handle_meta_command("/provider") is False

    # Switch provider
    with patch("aishell.providers.factory.get_provider") as mock_get_p:
        mock_new = MagicMock()
        mock_new.name = "openai"
        mock_new.model = "gpt-4o"
        mock_get_p.return_value = mock_new

        assert repl.handle_meta_command("/provider openai") is False
        assert repl.provider.name == "openai"


def test_repl_model_meta_commands():
    test_console = Console(file=MagicMock())
    repl = InteractiveREPL(console=test_console)

    # Inspect active model
    assert repl.handle_meta_command("/model") is False

    # Switch model
    with patch("aishell.providers.factory.get_provider") as mock_get_p:
        mock_new = MagicMock()
        mock_new.name = repl.provider.name
        mock_new.model = "mistral:latest"
        mock_get_p.return_value = mock_new

        assert repl.handle_meta_command("/model mistral:latest") is False
        assert repl.provider.model == "mistral:latest"


def test_repl_dispatch_ai_query_streams_from_provider():
    test_console = Console(file=MagicMock())
    mock_provider = MagicMock()
    mock_provider.name = "ollama"
    mock_provider.model = "qwen2.5-coder:7b"

    async def fake_stream(_messages):
        yield "Use `htop` "
        yield "to monitor processes."

    mock_provider.stream_chat = fake_stream

    repl = InteractiveREPL(console=test_console, provider=mock_provider)
    repl.dispatch_input("how do I monitor CPU usage?")

    assert repl.is_streaming is False


def test_repl_dispatch_ai_query_handles_provider_error_gracefully():
    test_console = Console(file=MagicMock())
    mock_provider = MagicMock()
    mock_provider.name = "gemini"
    mock_provider.model = "gemini-2.0-flash"

    async def failing_stream(_messages):
        raise AuthenticationError("gemini")
        yield "never"

    mock_provider.stream_chat = failing_stream

    repl = InteractiveREPL(console=test_console, provider=mock_provider)
    # Should not raise exception out of dispatch_input
    repl.dispatch_input("find large files")
    assert repl.is_streaming is False

