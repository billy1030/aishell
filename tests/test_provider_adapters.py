"""Unit tests for modular AI provider adapters (Ollama, OpenAI, Gemini, Anthropic)."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from openai import APIConnectionError, AuthenticationError as OpenAIAuthError, NotFoundError

from aishell.providers.anthropic import AnthropicProvider
from aishell.providers.base import ChatMessage
from aishell.providers.errors import (
    AuthenticationError,
    ConnectionError,
    ModelNotFoundError,
    RateLimitError,
)
from aishell.providers.gemini import GeminiProvider
from aishell.providers.ollama import OllamaProvider
from aishell.providers.openai import OpenAIProvider


# ---------------------------------------------------------
# OllamaProvider Tests
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_ollama_stream_chat_success():
    provider = OllamaProvider(model="qwen2.5-coder:7b")

    mock_chunk1 = MagicMock()
    mock_chunk1.choices = [MagicMock(delta=MagicMock(content="echo "))]
    mock_chunk2 = MagicMock()
    mock_chunk2.choices = [MagicMock(delta=MagicMock(content="'hello'"))]

    async def fake_stream():
        for chunk in [mock_chunk1, mock_chunk2]:
            yield chunk

    with patch.object(provider.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = fake_stream()
        chunks = []
        async for token in provider.stream_chat([ChatMessage(role="user", content="hi")]):
            chunks.append(token)

        assert "".join(chunks) == "echo 'hello'"


@pytest.mark.asyncio
async def test_ollama_stream_connection_error():
    provider = OllamaProvider()

    with patch.object(provider.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = APIConnectionError(request=MagicMock())
        with pytest.raises(ConnectionError) as exc_info:
            async for _ in provider.stream_chat([ChatMessage(role="user", content="hi")]):
                pass
        assert "ollama" in exc_info.value.provider.lower()
        assert "ollama serve" in exc_info.value.guidance


@pytest.mark.asyncio
async def test_ollama_generate_proposal_model_not_found():
    provider = OllamaProvider(model="nonexistent-model")

    with patch.object(provider.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = NotFoundError(
            message="model not found", response=MagicMock(status_code=404), body=None
        )
        with pytest.raises(ModelNotFoundError) as exc_info:
            await provider.generate_proposal("check disk")
        assert "nonexistent-model" in str(exc_info.value)
        assert "ollama pull" in exc_info.value.guidance


# ---------------------------------------------------------
# OpenAIProvider Tests
# ---------------------------------------------------------

def test_openai_validate_credentials_missing():
    provider = OpenAIProvider(api_key="")
    with pytest.raises(AuthenticationError) as exc_info:
        provider.validate_credentials()
    assert "OPENAI_API_KEY" in exc_info.value.guidance


@pytest.mark.asyncio
async def test_openai_auth_error_mapping():
    provider = OpenAIProvider(api_key="invalid-key")

    with patch.object(provider.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = OpenAIAuthError(
            message="Incorrect API key", response=MagicMock(status_code=401), body=None
        )
        with pytest.raises(AuthenticationError):
            await provider.generate_proposal("list files")


@pytest.mark.asyncio
async def test_openai_generate_proposal_success():
    provider = OpenAIProvider(api_key="valid-key")

    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(
                content='{"command": "ls -la", "purpose": "List directory contents", "risk_tier": "safe"}'
            )
        )
    ]

    with patch.object(provider.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_resp
        proposal = await provider.generate_proposal("list directory files")
        assert proposal.command == "ls -la"
        assert proposal.risk_tier == "safe"


# ---------------------------------------------------------
# GeminiProvider Tests
# ---------------------------------------------------------

def test_gemini_validate_credentials_missing():
    provider = GeminiProvider(api_key="")
    with pytest.raises(AuthenticationError) as exc_info:
        provider.validate_credentials()
    assert "GEMINI_API_KEY" in exc_info.value.guidance


@pytest.mark.asyncio
async def test_gemini_stream_chat_success():
    provider = GeminiProvider(api_key="valid-key")

    mock_chunk1 = MagicMock(text="find ")
    mock_chunk2 = MagicMock(text="/tmp")

    async def fake_stream():
        for chunk in [mock_chunk1, mock_chunk2]:
            yield chunk

    mock_client = MagicMock()
    mock_client.aio.models.generate_content_stream = AsyncMock(return_value=fake_stream())
    provider._client = mock_client

    tokens = []
    async for t in provider.stream_chat([ChatMessage(role="user", content="find tmp")]):
        tokens.append(t)
    assert "".join(tokens) == "find /tmp"


# ---------------------------------------------------------
# AnthropicProvider Tests
# ---------------------------------------------------------

def test_anthropic_validate_credentials_missing():
    provider = AnthropicProvider(api_key="")
    with pytest.raises(AuthenticationError) as exc_info:
        provider.validate_credentials()
    assert "ANTHROPIC_API_KEY" in exc_info.value.guidance


@pytest.mark.asyncio
async def test_anthropic_generate_proposal_success():
    provider = AnthropicProvider(api_key="valid-key")

    mock_resp = MagicMock()
    mock_block = MagicMock()
    mock_block.text = '{"command": "ps aux", "purpose": "List running processes", "risk_tier": "safe"}'
    mock_resp.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_resp)
    provider._client = mock_client

    proposal = await provider.generate_proposal("show processes")
    assert proposal.command == "ps aux"
    assert proposal.purpose == "List running processes"
    assert proposal.risk_tier == "safe"

