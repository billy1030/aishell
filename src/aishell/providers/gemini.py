"""Google Gemini provider adapter using the modern google-genai SDK."""

import os
from typing import AsyncIterator, List, Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError

from aishell.providers.base import BaseProvider, ChatMessage
from aishell.providers.errors import (
    AuthenticationError,
    ConnectionError,
    ProviderError,
    RateLimitError,
)
from aishell.providers.prompts import SYSTEM_PROMPT_COMMAND
from aishell.providers.schema import CommandProposal, parse_proposal_from_text


class GeminiProvider(BaseProvider):
    """Google Gemini AI provider adapter using official google-genai SDK."""

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key: Optional[str] = None,
    ) -> None:
        super().__init__(name="gemini", model=model)
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.environ.get("GEMINI_API_KEY")
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self.validate_credentials()
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def validate_credentials(self) -> None:
        """Validate GEMINI_API_KEY is present."""
        if not self.api_key or not self.api_key.strip():
            raise AuthenticationError(
                provider="gemini",
                message="Google Gemini API key is missing.",
            )

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Asynchronously stream tokens from Google Gemini."""
        client = self._get_client()

        # Format messages for Gemini contents
        contents = []
        for msg in messages:
            role = "model" if msg.role == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.content)]))

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
        ) if system_prompt else None

        try:
            response = await client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=config,
            )
            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except APIError as exc:
            if exc.code == 401 or exc.code == 403:
                raise AuthenticationError(
                    provider="gemini",
                    message=f"Gemini authentication failed: {exc}",
                ) from exc
            elif exc.code == 429:
                raise RateLimitError(
                    provider="gemini",
                    message=f"Gemini rate limit or quota exceeded: {exc}",
                ) from exc
            raise ProviderError(
                message=f"Gemini API error ({exc.code}): {exc}",
                guidance="Verify your Google Gemini project quota and API key status.",
            ) from exc
        except Exception as exc:
            raise ProviderError(
                message=f"Gemini error: {exc}",
                guidance="Check your network connection to Google Gemini API.",
            ) from exc

    async def generate_proposal(
        self,
        query: str,
        system_context: Optional[str] = None,
    ) -> CommandProposal:
        """Generate a structured command proposal via Google Gemini."""
        client = self._get_client()

        system_instructions = SYSTEM_PROMPT_COMMAND
        if system_context:
            system_instructions += f"\n\nTARGET SYSTEM CONTEXT:\n{system_context}"

        config = types.GenerateContentConfig(
            system_instruction=system_instructions,
            temperature=0.1,
        )

        try:
            response = await client.aio.models.generate_content(
                model=self.model,
                contents=query,
                config=config,
            )
            content = response.text or ""
            return parse_proposal_from_text(content)

        except APIError as exc:
            if exc.code in (401, 403):
                raise AuthenticationError(
                    provider="gemini",
                    message=f"Gemini authentication failed: {exc}",
                ) from exc
            elif exc.code == 429:
                raise RateLimitError(
                    provider="gemini",
                    message=f"Gemini quota exceeded: {exc}",
                ) from exc
            raise ProviderError(
                message=f"Gemini API error ({exc.code}): {exc}",
                guidance="Verify your Google Gemini project quota and API key status.",
            ) from exc
        except Exception as exc:
            raise ProviderError(
                message=f"Gemini proposal generation error: {exc}",
                guidance="Check your network connection to Google Gemini API.",
            ) from exc

