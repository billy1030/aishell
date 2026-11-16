"""Ollama provider adapter using OpenAI-compatible local API."""

from typing import AsyncIterator, List, Optional
import httpx
from openai import AsyncOpenAI
from openai import APIConnectionError, NotFoundError

from aishell.providers.base import BaseProvider, ChatMessage
from aishell.providers.errors import ConnectionError, ModelNotFoundError, ProviderError
from aishell.providers.prompts import SYSTEM_PROMPT_COMMAND
from aishell.providers.schema import CommandProposal, parse_proposal_from_text


class OllamaProvider(BaseProvider):
    """Local offline provider utilizing Ollama's OpenAI-compatible /v1 endpoint."""

    def __init__(
        self,
        model: str = "qwen2.5-coder:7b",
        base_url: str = "http://localhost:11434/v1",
        api_key: str = "ollama",
    ) -> None:
        super().__init__(name="ollama", model=model)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)

    def validate_credentials(self) -> None:
        """Validate base_url is specified."""
        if not self.base_url:
            raise ConnectionError(
                provider="ollama",
                url=self.base_url,
                message="Ollama base_url is not configured.",
            )

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Asynchronously stream tokens from local Ollama daemon."""
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
            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content

        except (APIConnectionError, httpx.ConnectError) as exc:
            raise ConnectionError(
                provider="ollama",
                url=self.base_url,
                message=f"Cannot connect to Ollama daemon at {self.base_url}",
            ) from exc
        except NotFoundError as exc:
            raise ModelNotFoundError(
                model=self.model,
                provider="ollama",
                message=f"Model '{self.model}' was not found on local Ollama service.",
            ) from exc
        except Exception as exc:
            raise ProviderError(
                message=f"Ollama stream error: {exc}",
                guidance=f"Check Ollama status at {self.base_url} or run 'ollama list'",
            ) from exc

    async def generate_proposal(
        self,
        query: str,
        system_context: Optional[str] = None,
    ) -> CommandProposal:
        """Generate a structured command proposal via Ollama."""
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

        except (APIConnectionError, httpx.ConnectError) as exc:
            raise ConnectionError(
                provider="ollama",
                url=self.base_url,
                message=f"Cannot connect to Ollama daemon at {self.base_url}",
            ) from exc
        except NotFoundError as exc:
            raise ModelNotFoundError(
                model=self.model,
                provider="ollama",
                message=f"Model '{self.model}' was not found on local Ollama service.",
            ) from exc
        except Exception as exc:
            raise ProviderError(
                message=f"Ollama proposal generation error: {exc}",
                guidance=f"Check Ollama status at {self.base_url} or run 'ollama list'",
            ) from exc

