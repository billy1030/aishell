"""Factory for resolving, instantiating, and validating AI provider adapters."""

from typing import Dict, Optional, Type
from aishell.config.settings import AishellSettings, get_settings
from aishell.providers.anthropic import AnthropicProvider
from aishell.providers.base import BaseProvider
from aishell.providers.errors import ProviderError
from aishell.providers.gemini import GeminiProvider
from aishell.providers.ollama import OllamaProvider
from aishell.providers.openai import OpenAIProvider

_PROVIDER_REGISTRY: Dict[str, Type[BaseProvider]] = {
    "ollama": OllamaProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}

_DEFAULT_MODELS: Dict[str, str] = {
    "ollama": "qwen2.5-coder:7b",
    "gemini": "gemini-2.0-flash",
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-sonnet-20241022",
}


def get_supported_providers() -> list[str]:
    """Return list of supported provider names."""
    return list(_PROVIDER_REGISTRY.keys())


def get_provider(
    name: Optional[str] = None,
    model: Optional[str] = None,
    settings: Optional[AishellSettings] = None,
    validate: bool = True,
) -> BaseProvider:
    """Instantiate and configure an AI provider adapter per D-04, PROV-01.

    Args:
        name: Name of provider ("ollama", "gemini", "openai", "anthropic").
              Defaults to settings.general.default_provider.
        model: Model name/identifier override.
        settings: AishellSettings instance.
        validate: Whether to invoke validate_credentials() on creation.

    Returns:
        Configured BaseProvider instance.

    Raises:
        ProviderError: If requested provider name is unsupported.
        AuthenticationError: If credentials for cloud provider are missing and validate=True.
        ConnectionError: If endpoint connection settings are invalid.
    """
    conf = settings or get_settings()
    provider_name = (name or conf.general.default_provider).strip().lower()

    if provider_name not in _PROVIDER_REGISTRY:
        supported = ", ".join(get_supported_providers())
        raise ProviderError(
            message=f"Unsupported provider '{provider_name}'. Supported providers: {supported}.",
            guidance=f"Choose one of the supported providers: {supported} via -p/--provider or in config.toml.",
        )

    # Determine model: explicit arg > settings.general.model (if matching provider) > provider default
    target_model = model
    if not target_model:
        if conf.general.default_provider.lower() == provider_name and conf.general.model:
            target_model = conf.general.model
        else:
            target_model = _DEFAULT_MODELS.get(provider_name, "default")

    # Instantiate provider with configured credentials
    provider: BaseProvider
    if provider_name == "ollama":
        ollama_cfg = conf.providers.ollama
        provider = OllamaProvider(
            model=target_model,
            base_url=ollama_cfg.base_url or "http://localhost:11434/v1",
        )
    elif provider_name == "gemini":
        gemini_cfg = conf.providers.gemini
        provider = GeminiProvider(
            model=target_model,
            api_key=gemini_cfg.api_key,
        )
    elif provider_name == "openai":
        openai_cfg = conf.providers.openai
        provider = OpenAIProvider(
            model=target_model,
            api_key=openai_cfg.api_key,
            base_url=openai_cfg.base_url,
        )
    elif provider_name == "anthropic":
        anthropic_cfg = conf.providers.anthropic
        provider = AnthropicProvider(
            model=target_model,
            api_key=anthropic_cfg.api_key,
            base_url=anthropic_cfg.base_url,
        )

    if validate:
        provider.validate_credentials()

    return provider

