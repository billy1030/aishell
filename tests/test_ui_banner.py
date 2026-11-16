"""Unit tests for banner rendering and prompt formatting."""

from io import StringIO
from pathlib import Path
import pytest
from rich.console import Console

from aishell.config.settings import AishellSettings
from aishell.ui.banner import (
    contract_path,
    format_prompt,
    format_prompt_string,
    get_prompt_style,
    render_banner,
)


def test_contract_path(tmp_path: Path):
    home = Path.home().resolve()
    # Direct home directory
    assert contract_path(str(home)) == "~"

    # Subdirectory of home
    sub = home / "projects" / "myrepo"
    assert contract_path(str(sub)) == "~/projects/myrepo"


def test_format_prompt_string():
    prompt_str = format_prompt_string(cwd="/var/log", model_name="qwen-coder")
    assert prompt_str.startswith("aishell [")
    assert "(qwen-coder)" in prompt_str
    assert prompt_str.endswith("> ")


def test_format_prompt_tokens():
    tokens = format_prompt(cwd="/tmp", model_name="gemini-2.0")
    text = "".join(tok[1] for tok in tokens)
    assert text.startswith("aishell [")
    assert "(gemini-2.0)" in text
    assert text.endswith("> ")

    # Check token classes
    token_dict = dict(tokens)
    assert "class:prompt.brand" in [tok[0] for tok in tokens]
    assert "class:prompt.path" in [tok[0] for tok in tokens]
    assert "class:prompt.model" in [tok[0] for tok in tokens]
    assert "class:prompt.symbol" in [tok[0] for tok in tokens]


def test_get_prompt_style():
    style = get_prompt_style()
    assert style is not None


def test_render_banner():
    string_io = StringIO()
    test_console = Console(file=string_io, force_terminal=True)
    settings = AishellSettings()

    render_banner(console=test_console, settings=settings)
    output = string_io.getvalue()

    assert "Terminal AI Shell" in output
    assert "aishell" in output
    assert "Python:" in output
    assert "AI Model:" in output
    assert "Alt+Enter" in output
    assert "Ctrl+R" in output
