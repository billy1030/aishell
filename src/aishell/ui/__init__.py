"""Terminal User Interface package for aishell."""

from aishell.ui.banner import (
    contract_path,
    format_prompt,
    format_prompt_string,
    get_prompt_style,
    render_banner,
)
from aishell.ui.history import SQLiteHistory
from aishell.ui.renderer import RichStreamRenderer, detect_terminal_capabilities

__all__ = [
    "RichStreamRenderer",
    "SQLiteHistory",
    "contract_path",
    "detect_terminal_capabilities",
    "format_prompt",
    "format_prompt_string",
    "get_prompt_style",
    "render_banner",
]
