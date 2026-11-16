"""Abstract BaseProvider protocol and conversational message models."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, AsyncIterator, List, Literal, Optional
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from aishell.providers.schema import CommandProposal


class ChatMessage(BaseModel):
    """Represents a conversational turn in an AI session."""

    role: Literal["system", "user", "assistant"] = Field(
        ..., description="Message author role"
    )
    content: str = Field(..., description="Message textual content")


class BaseProvider(ABC):
    """Abstract base class for all aishell model provider adapters."""

    def __init__(self, name: str, model: str) -> None:
        self.name = name
        self.model = model

    @abstractmethod
    def validate_credentials(self) -> None:
        """Validate API key presence or endpoint reachability.

        Raises:
            AuthenticationError: If required credentials are missing.
            ConnectionError: If endpoint cannot be resolved.
        """
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[ChatMessage],
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Asynchronously stream tokens for multi-turn conversation.

        Args:
            messages: List of prior conversational messages.
            system_prompt: Optional system instruction prompt.

        Yields:
            Token text strings as received from the provider.
        """
        pass

    @abstractmethod
    async def generate_proposal(
        self,
        query: str,
        system_context: Optional[str] = None,
    ) -> "CommandProposal":
        """Generate a structured command proposal with risk assessment.

        Args:
            query: Natural language operator query.
            system_context: Optional system facts (OS, distro, cwd, etc.).

        Returns:
            Validated CommandProposal instance.
        """
        pass
