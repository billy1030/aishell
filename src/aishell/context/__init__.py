"""Host system context inspection and environment discovery for aishell."""

from aishell.context.inspector import (
    detect_git_status,
    detect_package_manager,
    inspect_system_context,
    is_root_user,
)
from aishell.context.schema import SystemContext

__all__ = [
    "SystemContext",
    "detect_git_status",
    "detect_package_manager",
    "inspect_system_context",
    "is_root_user",
]
