"""Anthropic Claude provider adapter using AsyncAnthropic client."""

import os
from typing import AsyncIterator, List, Optional
import httpx
from anthropic import (
    APIConnectionError,
    AsyncAnthropic,
    AuthenticationError as AnthropicAuthError,
    RateLimitError as AnthropicRateLimitError,
)

from aishell.providers.base import BaseProvider, ChatMessage
from aishell.providers.errors import (
    AuthenticationError,
    ConnectionError,
    ProviderError,
    RateLimitError,
)
from aishell.providers.prompts import SYSTEM_PROMPT_COMMAND
from aishell.providers.schema import CommandProposal, parse_proposal_from_text


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider adapter."""

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        super().__init__(name="anthropic", model=model)
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.base_url = base_url
        self._client: Optional[AsyncAnthropic] = None

    def _get_client(self) -> AsyncAnthropic:
        if self._client is None:
            self.validate_credentials()
            self._client = AsyncAnthropic(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def validate_credentials(self) -> None:
        """Validate ANTHROPIC_API_KEY is present."""
        if not self.api_key or not self.api_key.strip():
            raise AuthenticationError(
                provider="anthropic",
                message="Anthropic API key is missing.",
            )

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Asynchronously stream tokens from Claude."""
        client = self._get_client()

        payload_messages = []
        for msg in messages:
            # Anthropic only accepts user and assistant roles in messages array
            role = "user" if msg.role in ("user", "system") else "assistant"
            payload_messages.append({"role": role, "content": msg.content})

        try:
            async with client.messages.stream(
                max_tokens=2048,
                model=self.model,
                messages=payload_messages,
                system=system_prompt,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except AnthropicAuthError as exc:
            raise AuthenticationError(
                provider="anthropic",
                message=f"Anthropic authentication failed: {exc}",
            ) from exc
        except AnthropicRateLimitError as exc:
            raise RateLimitError(
                provider="anthropic",
                message=f"Anthropic rate limit or quota exceeded: {exc}",
            ) from exc
        except (APIConnectionError, httpx.ConnectError) as exc:
            raise ConnectionError(
                provider="anthropic",
                url=self.base_url or "https://api.anthropic.com",
                message="Cannot connect to Anthropic API endpoint.",
            ) from exc
        except Exception as exc:
            raise ProviderError(
                message=f"Anthropic error: {exc}",
                guidance="Check your Anthropic API key and network connection.",
            ) from exc

    async def generate_proposal(
        self,
        query: str,
        system_context: Optional[str] = None,
    ) -> CommandProposal:
        """Generate a structured command proposal via Claude."""
        client = self._get_client()

        system_instructions = SYSTEM_PROMPT_COMMAND
        if system_context:
            system_instructions += f"\n\nTARGET SYSTEM CONTEXT:\n{system_context}"

        try:
            response = await client.messages.create(
                max_tokens=1024,
                model=self.model,
                system=system_instructions,
                messages=[{"role": "user", "content": query}],
            )
            # Extract content text blocks
            text_blocks = [
                block.text for block in response.content if hasattr(block, "text")
            ]
            content = "\n".join(text_blocks)
            return parse_proposal_from_text(content)

        except AnthropicAuthError as exc:
            raise AuthenticationError(
                provider="anthropic",
                message=f"Anthropic authentication failed: {exc}",
            ) from exc
        except AnthropicRateLimitError as exc:
            raise RateLimitError(
                provider="anthropic",
                message=f"Anthropic rate limit or quota exceeded: {exc}",
            ) from exc
        except (APIConnectionError, httpx.ConnectError) as exc:
            raise ConnectionError(
                provider="anthropic",
                url=self.base_url or "https://api.anthropic.com",
                message="Cannot connect to Anthropic API endpoint.",
            ) from exc
        except Exception as exc:
            raise ProviderError(
                message=f"Anthropic proposal generation error: {exc}",
                guidance="Check your Anthropic API key and network connection.",
            ) from exc

