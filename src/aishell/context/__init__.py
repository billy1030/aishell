"""Host system context inspection, privacy guard, and observation sanitizer."""

from aishell.context.inspector import (
    detect_git_status,
    detect_package_manager,
    inspect_system_context,
    is_root_user,
)
from aishell.context.privacy import PrivacyGuard
from aishell.context.sanitizer import format_system_observation, sanitize_boundary_text
from aishell.context.schema import SystemContext

__all__ = [
    "PrivacyGuard",
    "SystemContext",
    "detect_git_status",
    "detect_package_manager",
    "format_system_observation",
    "inspect_system_context",
    "is_root_user",
    "sanitize_boundary_text",
]
