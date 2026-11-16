"""Unit tests for ProviderError hierarchy and actionable guidance."""

from aishell.providers.errors import (
    AuthenticationError,
    ConnectionError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
)


def test_provider_error_base():
    err = ProviderError("Something failed", guidance="Try running with --debug")
    assert "Something failed" in str(err)
    assert "Try running with --debug" in err.guidance
    assert "Guidance: Try running with --debug" in str(err)


def test_authentication_error_gemini():
    err = AuthenticationError("gemini")
    assert err.provider == "gemini"
    assert "GEMINI_API_KEY" in err.guidance
    assert "export GEMINI_API_KEY=" in err.guidance
    assert "config.toml" in err.guidance


def test_authentication_error_openai():
    err = AuthenticationError("openai")
    assert err.provider == "openai"
    assert "OPENAI_API_KEY" in err.guidance
    assert "export OPENAI_API_KEY=" in err.guidance


def test_authentication_error_anthropic():
    err = AuthenticationError("anthropic")
    assert err.provider == "anthropic"
    assert "ANTHROPIC_API_KEY" in err.guidance


def test_connection_error_ollama():
    err = ConnectionError("ollama", url="http://localhost:11434")
    assert err.provider == "ollama"
    assert "ollama serve" in err.guidance
    assert "http://localhost:11434" in str(err)


def test_connection_error_cloud_provider():
    err = ConnectionError("openai")
    assert "proxy settings" in err.guidance.lower() or "network" in err.guidance.lower()


def test_rate_limit_error():
    err = RateLimitError("anthropic")
    assert err.provider == "anthropic"
    assert "switch" in err.guidance.lower()
    assert "--provider" in err.guidance


def test_model_not_found_error_ollama():
    err = ModelNotFoundError("qwen2.5-coder:32b", "ollama")
    assert err.model == "qwen2.5-coder:32b"
    assert err.provider == "ollama"
    assert "ollama pull qwen2.5-coder:32b" in err.guidance


def test_model_not_found_error_cloud():
    err = ModelNotFoundError("gpt-5", "openai")
    assert "config.toml" in err.guidance
