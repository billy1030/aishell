"""Factory for resolving, instantiating, and validating AI provider adapters."""

import os
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
    "minimax": OpenAIProvider,
}

_DEFAULT_MODELS: Dict[str, str] = {
    "ollama": "qwen2.5-coder:7b",
    "gemini": "gemini-2.0-flash",
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-sonnet-20241022",
    "minimax": "MiniMax-M3.1-Flash",
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
        name: Name of provider ("minimax", "ollama", "gemini", "openai", "anthropic", or custom).
              Defaults to settings.general.default_provider.
        model: Model name/identifier override.
        settings: AishellSettings instance.
        validate: Whether to invoke validate_credentials() on creation.

    Returns:
        Configured BaseProvider instance.
    """
    conf = settings or get_settings()
    provider_name = (name or conf.general.default_provider).strip().lower()

    # Determine model: explicit arg > [providers.<name>].model > [general].model (if primary) > provider default
    provider_cfg = conf.providers.get_provider_config(provider_name)
    target_model = model
    if not target_model:
        if provider_cfg.model:
            target_model = provider_cfg.model
        elif conf.general.default_provider.lower() == provider_name and conf.general.model:
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
            name="openai",
            model=target_model,
            api_key=openai_cfg.api_key,
            base_url=openai_cfg.base_url,
        )
    elif provider_name == "minimax":
        minimax_cfg = conf.providers.get_provider_config("minimax")
        api_key = (
            minimax_cfg.api_key
            or conf.providers.openai.api_key
            or os.environ.get("MINIMAX_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )
        base_url = (
            minimax_cfg.base_url
            or conf.providers.openai.base_url
            or "https://api.minimaxi.com/v1"
        )
        provider = OpenAIProvider(
            name="minimax",
            model=target_model,
            api_key=api_key,
            base_url=base_url,
        )
    elif provider_name == "anthropic":
        anthropic_cfg = conf.providers.anthropic
        provider = AnthropicProvider(
            model=target_model,
            api_key=anthropic_cfg.api_key,
            base_url=anthropic_cfg.base_url,
        )
    else:
        # Universal OpenAI-compatible provider resolution based on config or env
        custom_cfg = conf.providers.get_provider_config(provider_name)
        env_prefix = provider_name.upper().replace("-", "_")
        api_key = (
            custom_cfg.api_key
            or os.environ.get(f"{env_prefix}_API_KEY")
            or conf.providers.openai.api_key
            or os.environ.get("OPENAI_API_KEY")
        )
        base_url = (
            custom_cfg.base_url
            or os.environ.get(f"{env_prefix}_BASE_URL")
            or conf.providers.openai.base_url
            or os.environ.get("OPENAI_BASE_URL")
        )
        provider = OpenAIProvider(
            name=provider_name,
            model=target_model,
            api_key=api_key,
            base_url=base_url,
        )

    if validate:
        provider.validate_credentials()

    return provider

