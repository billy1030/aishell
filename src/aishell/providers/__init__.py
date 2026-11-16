"""AI provider abstraction, schema, adapters, and factory for aishell."""

from aishell.providers.anthropic import AnthropicProvider
from aishell.providers.base import BaseProvider, ChatMessage
from aishell.providers.errors import (
    AuthenticationError,
    ConnectionError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
)
from aishell.providers.factory import get_provider, get_supported_providers
from aishell.providers.gemini import GeminiProvider
from aishell.providers.ollama import OllamaProvider
from aishell.providers.openai import OpenAIProvider
from aishell.providers.prompts import SYSTEM_PROMPT_CHAT, SYSTEM_PROMPT_COMMAND
from aishell.providers.schema import CommandProposal, parse_proposal_from_text

__all__ = [
    "AnthropicProvider",
    "AuthenticationError",
    "BaseProvider",
    "ChatMessage",
    "CommandProposal",
    "ConnectionError",
    "GeminiProvider",
    "ModelNotFoundError",
    "OllamaProvider",
    "OpenAIProvider",
    "ProviderError",
    "RateLimitError",
    "SYSTEM_PROMPT_CHAT",
    "SYSTEM_PROMPT_COMMAND",
    "get_provider",
    "get_supported_providers",
    "parse_proposal_from_text",
]
