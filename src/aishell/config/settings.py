"""Configuration management for aishell using Pydantic Settings."""

import os
from pathlib import Path
from typing import Any, List, Optional, Tuple, Type
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


def get_default_config_dir() -> Path:
    """Get the default configuration directory following XDG standards."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "aishell"
    return Path.home() / ".config" / "aishell"


def get_default_config_path() -> Path:
    """Get the default config.toml path."""
    custom_path = os.environ.get("AISHELL_CONFIG_FILE")
    if custom_path:
        return Path(custom_path)
    return get_default_config_dir() / "config.toml"


def get_default_state_dir() -> Path:
    """Get the default state directory following XDG standards."""
    xdg_state = os.environ.get("XDG_STATE_HOME")
    if xdg_state:
        return Path(xdg_state) / "aishell"
    return Path.home() / ".local" / "state" / "aishell"


def get_default_history_db_path() -> Path:
    """Get the default history.db path."""
    return get_default_state_dir() / "history.db"


class GeneralConfig(BaseModel):
    """General shell assistant configuration."""

    default_provider: str = Field(default="ollama", description="Active AI provider")
    model: str = Field(default="qwen2.5-coder:7b", description="Model name or endpoint identifier")
    theme: str = Field(default="dark", description="Terminal theme: dark or light")
    max_agent_steps: int = Field(default=100, description="Maximum autonomous agent loop steps per goal")
    system_prompt: Optional[str] = Field(default=None, description="Custom system prompt appended to assistant instructions")
    ai_triggers: List[str] = Field(
        default_factory=lambda: ["hi", "hello", "hey", "please", "ais", "ai", "help"],
        description="Keywords/prefixes that wake the AI assistant in the REPL",
    )


class ExecutionConfig(BaseModel):
    """Shell execution engine configuration."""

    timeout_seconds: float = Field(default=300.0, description="Process execution timeout")
    max_output_buffer_kb: int = Field(default=50, description="Max in-memory output buffer in KB")
    ring_buffer_lines: int = Field(default=1000, description="Max in-memory lines retained")


class StorageConfig(BaseModel):
    """Audit and history persistence configuration."""

    history_db_path: Path = Field(
        default_factory=get_default_history_db_path,
        description="Path to SQLite history database",
    )
    max_history_records: int = Field(
        default=10000, description="FIFO history retention limit"
    )


class ProviderConfig(BaseModel):
    """Individual provider settings."""

    api_key: Optional[str] = Field(default=None, description="API key or token")
    base_url: Optional[str] = Field(default=None, description="Custom endpoint base URL")


class ProvidersConfig(BaseModel):
    """AI providers collection, supporting standard and arbitrary custom providers."""

    model_config = ConfigDict(extra="allow")

    gemini: ProviderConfig = Field(default_factory=ProviderConfig)
    openai: ProviderConfig = Field(default_factory=ProviderConfig)
    anthropic: ProviderConfig = Field(default_factory=ProviderConfig)
    ollama: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(base_url="http://localhost:11434/v1")
    )
    minimax: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(base_url="https://api.minimaxi.com/v1")
    )

    def get_provider_config(self, name: str) -> ProviderConfig:
        """Get provider config by name, returning custom extra config or default."""
        name_lower = name.lower()
        if hasattr(self, name_lower):
            val = getattr(self, name_lower)
            if isinstance(val, ProviderConfig):
                return val
        # Check extra attributes (e.g. [providers.deepseek] or [providers.custom] in TOML)
        extra = getattr(self, "__pydantic_extra__", {}) or {}
        if name_lower in extra:
            raw = extra[name_lower]
            if isinstance(raw, dict):
                return ProviderConfig(**raw)
            if isinstance(raw, ProviderConfig):
                return raw
        return ProviderConfig()


class AishellSettings(BaseSettings):
    """Layered configuration for aishell.

    Precedence order:
    1. CLI argument overrides (handled by caller)
    2. Environment variables prefixed with AISHELL_ (e.g. AISHELL_GENERAL__DEFAULT_PROVIDER)
    3. Vendor API keys from environment (GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY)
    4. ~/.config/aishell/config.toml (or custom path from XDG_CONFIG_HOME / AISHELL_CONFIG_FILE)
    5. Pydantic default field values
    """

    model_config = SettingsConfigDict(
        env_prefix="AISHELL_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    config_file: Optional[Path] = Field(default=None, exclude=True)

    general: GeneralConfig = Field(default_factory=GeneralConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)

    def model_post_init(self, __context: Any) -> None:
        """Inject vendor environment variables if not explicitly provided."""
        if not self.providers.gemini.api_key:
            self.providers.gemini.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.providers.openai.api_key:
            self.providers.openai.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.providers.anthropic.api_key:
            self.providers.anthropic.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.providers.minimax.api_key:
            self.providers.minimax.api_key = os.environ.get("MINIMAX_API_KEY")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """Customise settings sources to load TOML config before defaults."""
        config_path = get_default_config_path()
        toml_source = TomlConfigSettingsSource(
            settings_cls, toml_file=config_path if config_path.is_file() else None
        )
        return (init_settings, env_settings, toml_source)


def load_settings(config_path: Optional[Path] = None) -> AishellSettings:
    """Load settings from the specified or default config file path."""
    if config_path and config_path.is_file():
        os.environ["AISHELL_CONFIG_FILE"] = str(config_path)
    return AishellSettings()


get_settings = load_settings

