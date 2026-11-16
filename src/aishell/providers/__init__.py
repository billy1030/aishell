"""AI provider abstraction, schema, and error handling for aishell."""

from aishell.providers.base import BaseProvider, ChatMessage
from aishell.providers.errors import (
    AuthenticationError,
    ConnectionError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
)
from aishell.providers.prompts import SYSTEM_PROMPT_CHAT, SYSTEM_PROMPT_COMMAND
from aishell.providers.schema import CommandProposal, parse_proposal_from_text

__all__ = [
    "AuthenticationError",
    "BaseProvider",
    "ChatMessage",
    "CommandProposal",
    "ConnectionError",
    "ModelNotFoundError",
    "ProviderError",
    "RateLimitError",
    "SYSTEM_PROMPT_CHAT",
    "SYSTEM_PROMPT_COMMAND",
    "parse_proposal_from_text",
]
