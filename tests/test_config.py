"""Tests for configuration loading and defaults."""

import os
import stat
from pathlib import Path
from aishell.config.settings import AishellSettings, load_settings
from aishell.config.defaults import ensure_default_config


def test_default_settings():
    """Verify that default settings load as expected."""
    settings = AishellSettings()
    assert settings.general.default_provider == "ollama"
    assert settings.general.model == "qwen2.5-coder:7b"
    assert settings.storage.max_history_records == 10000
    assert settings.execution.ring_buffer_lines == 1000


def test_env_var_override(monkeypatch):
    """Verify that AISHELL_ prefixed env vars override defaults."""
    monkeypatch.setenv("AISHELL_GENERAL__DEFAULT_PROVIDER", "gemini")
    monkeypatch.setenv("AISHELL_GENERAL__MODEL", "gemini-2.0-flash")
    monkeypatch.setenv("AISHELL_STORAGE__MAX_HISTORY_RECORDS", "5000")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    settings = AishellSettings()
    assert settings.general.default_provider == "gemini"
    assert settings.general.model == "gemini-2.0-flash"
    assert settings.storage.max_history_records == 5000
    assert settings.providers.gemini.api_key == "test-gemini-key"


def test_toml_loading_and_env_precedence(tmp_path, monkeypatch):
    """Verify that TOML overrides defaults and env vars override TOML."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[general]
default_provider = "openai"
model = "gpt-4o"

[storage]
max_history_records = 2000
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("AISHELL_CONFIG_FILE", str(config_file))
    # No env override for default_provider -> should take TOML value
    settings = load_settings(config_file)
    assert settings.general.default_provider == "openai"
    assert settings.general.model == "gpt-4o"
    assert settings.storage.max_history_records == 2000

    # Add env override -> should take env value over TOML
    monkeypatch.setenv("AISHELL_GENERAL__MODEL", "o3-mini")
    settings2 = load_settings(config_file)
    assert settings2.general.model == "o3-mini"
    assert settings2.general.default_provider == "openai"


def test_ensure_default_config(tmp_path):
    """Verify that default config is created with secure permissions."""
    target_config = tmp_path / "subdir" / "config.toml"
    assert not target_config.exists()

    result_path = ensure_default_config(target_config)
    assert result_path.exists()
    assert "[general]" in result_path.read_text(encoding="utf-8")

    # On POSIX systems, verify file and directory permissions
    if os.name != "nt":
        file_mode = stat.S_IMODE(os.stat(result_path).st_mode)
        dir_mode = stat.S_IMODE(os.stat(result_path.parent).st_mode)
        assert file_mode == 0o600
        assert dir_mode == 0o700
