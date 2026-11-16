"""Exception hierarchy for AI providers with actionable operator guidance."""

from typing import Optional


class ProviderError(Exception):
    """Base exception for all AI provider operations."""

    def __init__(self, message: str, guidance: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.guidance = guidance or ""

    def __str__(self) -> str:
        if self.guidance:
            return f"{self.message}\nGuidance: {self.guidance}"
        return self.message


class AuthenticationError(ProviderError):
    """Raised when provider credentials are missing or invalid."""

    ENV_VAR_MAP = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }

    def __init__(self, provider: str, message: Optional[str] = None) -> None:
        p_lower = provider.lower()
        env_var = self.ENV_VAR_MAP.get(p_lower, f"{provider.upper()}_API_KEY")
        default_msg = f"Authentication failed for provider '{provider}'."
        guidance = (
            f"Set your API key via environment variable: export {env_var}='your-key-here'\n"
            f"Or configure it in ~/.config/aishell/config.toml under [providers.{p_lower}]."
        )
        super().__init__(message or default_msg, guidance=guidance)
        self.provider = provider


class ConnectionError(ProviderError):
    """Raised when connection to provider or local daemon fails."""

    def __init__(self, provider: str, url: Optional[str] = None, message: Optional[str] = None) -> None:
        p_lower = provider.lower()
        target = f" at {url}" if url else ""
        default_msg = f"Could not connect to {provider}{target}."
        if p_lower == "ollama":
            guidance = (
                f"Ensure the local Ollama daemon is running at {url or 'http://localhost:11434'}.\n"
                "Start it with: 'ollama serve' or check 'systemctl status ollama'."
            )
        else:
            guidance = f"Check your network connection and proxy settings to reach {provider}."
        super().__init__(message or default_msg, guidance=guidance)
        self.provider = provider
        self.url = url


class RateLimitError(ProviderError):
    """Raised when provider rate limits or token quotas are exceeded."""

    def __init__(self, provider: str, message: Optional[str] = None) -> None:
        default_msg = f"Rate limit or quota exceeded for {provider}."
        guidance = (
            "Wait a few seconds before retrying, or switch to an alternate provider "
            "using '--provider <name>' or in the REPL via ':provider <name>'."
        )
        super().__init__(message or default_msg, guidance=guidance)
        self.provider = provider


class ModelNotFoundError(ProviderError):
    """Raised when the specified model does not exist on the provider."""

    def __init__(self, model: str, provider: str, message: Optional[str] = None) -> None:
        p_lower = provider.lower()
        default_msg = f"Model '{model}' was not found on provider '{provider}'."
        if p_lower == "ollama":
            guidance = f"Pull the model first by running: 'ollama pull {model}'."
        else:
            guidance = f"Verify the model name '{model}' in ~/.config/aishell/config.toml or pass a supported model via '-m'."
        super().__init__(message or default_msg, guidance=guidance)
        self.model = model
        self.provider = provider
