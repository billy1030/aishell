"""Terminal User Interface package for aishell."""

from aishell.ui.renderer import RichStreamRenderer, detect_terminal_capabilities

__all__ = [
    "RichStreamRenderer",
    "detect_terminal_capabilities",
]
