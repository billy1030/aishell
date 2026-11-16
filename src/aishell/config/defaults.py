"""Default configuration generator for aishell."""

import os
from pathlib import Path
from typing import Optional
from aishell.config.settings import get_default_config_dir, get_default_config_path

DEFAULT_CONFIG_TEMPLATE = """# aishell configuration file
# Location: ~/.config/aishell/config.toml

[general]
# Default provider: ollama, gemini, openai, or anthropic
default_provider = "ollama"
# Default model name
model = "qwen2.5-coder:7b"
# Terminal theme: dark or light
theme = "dark"

[execution]
# Subprocess timeout in seconds
timeout_seconds = 300.0
# Maximum output buffer size in KB retained in memory
max_output_buffer_kb = 50
# Maximum lines retained in circular ring buffer
ring_buffer_lines = 1000

[storage]
# Maximum number of history commands to retain (FIFO pruning)
max_history_records = 10000

[providers.ollama]
base_url = "http://localhost:11434/v1"

[providers.gemini]
# api_key can also be set via GEMINI_API_KEY environment variable

[providers.openai]
# api_key can also be set via OPENAI_API_KEY environment variable

[providers.anthropic]
# api_key can also be set via ANTHROPIC_API_KEY environment variable
"""


def ensure_default_config(config_path: Optional[Path] = None) -> Path:
    """Ensure that config.toml exists with sensible defaults and secure permissions.

    Enforces 0700 directory permissions and 0600 file permissions per D-15.
    Returns the resolved Path to the config file.
    """
    path = config_path or get_default_config_path()
    parent_dir = path.parent

    # Ensure parent directory exists with 0700 permissions
    if not parent_dir.exists():
        parent_dir.mkdir(parents=True, exist_ok=True)
        try:
            if hasattr(os, "chmod") and os.name != "nt":
                os.chmod(parent_dir, 0o700)
        except OSError:
            pass

    # If file doesn't exist, create it with default template and 0600 permissions
    if not path.exists():
        path.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
        try:
            if hasattr(os, "chmod") and os.name != "nt":
                os.chmod(path, 0o600)
        except OSError:
            pass

    return path
