"""Unit tests for get_provider factory, registration, and credential validation."""

import pytest
from aishell.config.settings import AishellSettings
from aishell.providers.anthropic import AnthropicProvider
from aishell.providers.errors import AuthenticationError, ProviderError
from aishell.providers.factory import get_provider, get_supported_providers
from aishell.providers.gemini import GeminiProvider
from aishell.providers.ollama import OllamaProvider
from aishell.providers.openai import OpenAIProvider


def test_get_supported_providers():
    supported = get_supported_providers()
    assert "ollama" in supported
    assert "gemini" in supported
    assert "openai" in supported
    assert "anthropic" in supported


def test_get_provider_default_ollama():
    settings = AishellSettings()
    provider = get_provider(settings=settings)
    assert isinstance(provider, OllamaProvider)
    assert provider.name == "ollama"
    assert provider.model == "qwen2.5-coder:7b"


def test_get_provider_model_override():
    settings = AishellSettings()
    provider = get_provider("ollama", model="deepseek-coder:6.7b", settings=settings)
    assert isinstance(provider, OllamaProvider)
    assert provider.model == "deepseek-coder:6.7b"


def test_get_provider_unsupported_fails():
    with pytest.raises(ProviderError) as exc_info:
        get_provider("unsupported_ai_vendor")
    assert "unsupported_ai_vendor" in str(exc_info.value)
    assert "Supported providers" in str(exc_info.value)


def test_get_provider_validation_checks_credentials():
    settings = AishellSettings()
    settings.providers.openai.api_key = None

    # validate=True should raise AuthenticationError
    with pytest.raises(AuthenticationError):
        get_provider("openai", settings=settings, validate=True)

    # validate=False allows instantiation
    provider = get_provider("openai", settings=settings, validate=False)
    assert isinstance(provider, OpenAIProvider)
    assert provider.name == "openai"


def test_get_provider_gemini_instantiation():
    settings = AishellSettings()
    settings.providers.gemini.api_key = "test-key"
    provider = get_provider("gemini", settings=settings, validate=True)
    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"
    assert provider.model == "gemini-2.0-flash"


def test_get_provider_anthropic_instantiation():
    settings = AishellSettings()
    settings.providers.anthropic.api_key = "test-key"
    provider = get_provider("anthropic", settings=settings, validate=True)
    assert isinstance(provider, AnthropicProvider)
    assert provider.name == "anthropic"

