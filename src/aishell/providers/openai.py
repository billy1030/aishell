"""OpenAI provider adapter using AsyncOpenAI client."""

import os
from typing import AsyncIterator, List, Optional
import httpx
from openai import AsyncOpenAI
from openai import (
    APIConnectionError,
    AuthenticationError as OpenAIAuthError,
    RateLimitError as OpenAIRateLimitError,
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


class OpenAIProvider(BaseProvider):
    """OpenAI API provider adapter for GPT models and OpenAI-compatible endpoints."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        name: str = "openai",
    ) -> None:
        super().__init__(name=name, model=model)
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = (
                os.environ.get(f"{name.upper()}_API_KEY")
                or os.environ.get("OPENAI_API_KEY")
            )
        self.base_url = base_url
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self.validate_credentials()
            self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    @property
    def client(self) -> AsyncOpenAI:
        return self._get_client()

    def validate_credentials(self) -> None:
        """Validate API key is present."""
        if not self.api_key or not self.api_key.strip():
            raise AuthenticationError(
                provider=self.name,
                message=f"{self.name.capitalize()} API key is missing.",
            )

    async def aclose(self) -> None:
        """Close the underlying AsyncOpenAI HTTP client cleanly."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Asynchronously stream tokens from OpenAI."""
        self.validate_credentials()

        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            payload_messages.append({"role": msg.role, "content": msg.content})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=payload_messages,
                stream=True,
            )
            async with response:
                async for chunk in response:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.content:
                        yield delta.content

        except OpenAIAuthError as exc:
            raise AuthenticationError(
                provider="openai",
                message=f"OpenAI authentication failed: {exc}",
            ) from exc
        except OpenAIRateLimitError as exc:
            raise RateLimitError(
                provider="openai",
                message=f"OpenAI rate limit or quota exceeded: {exc}",
            ) from exc
        except (APIConnectionError, httpx.ConnectError) as exc:
            raise ConnectionError(
                provider="openai",
                url=self.base_url or "https://api.openai.com/v1",
                message="Cannot connect to OpenAI API endpoint.",
            ) from exc
        except Exception as exc:
            raise ProviderError(
                message=f"OpenAI error: {exc}",
                guidance="Check your OpenAI API key and network connection.",
            ) from exc

    async def generate_proposal(
        self,
        query: str,
        system_context: Optional[str] = None,
    ) -> CommandProposal:
        """Generate a structured command proposal via OpenAI."""
        self.validate_credentials()

        system_instructions = SYSTEM_PROMPT_COMMAND
        if system_context:
            system_instructions += f"\n\nTARGET SYSTEM CONTEXT:\n{system_context}"

        messages = [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": query},
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
            )
            content = response.choices[0].message.content or ""
            return parse_proposal_from_text(content)

        except OpenAIAuthError as exc:
            raise AuthenticationError(
                provider="openai",
                message=f"OpenAI authentication failed: {exc}",
            ) from exc
        except OpenAIRateLimitError as exc:
            raise RateLimitError(
                provider="openai",
                message=f"OpenAI rate limit or quota exceeded: {exc}",
            ) from exc
        except (APIConnectionError, httpx.ConnectError) as exc:
            raise ConnectionError(
                provider="openai",
                url=self.base_url or "https://api.openai.com/v1",
                message="Cannot connect to OpenAI API endpoint.",
            ) from exc
        except Exception as exc:
            raise ProviderError(
                message=f"OpenAI proposal generation error: {exc}",
                guidance="Check your OpenAI API key and network connection.",
            ) from exc

