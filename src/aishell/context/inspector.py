"""System context inspector probing host OS, kernel, privileges, and git state."""

import getpass
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import distro

from aishell.context.schema import SystemContext

# Order of package manager priority lookup
_PACKAGE_MANAGERS = [
    ("apt", ["apt-get", "apt"]),
    ("dnf", ["dnf"]),
    ("pacman", ["pacman"]),
    ("apk", ["apk"]),
    ("zypper", ["zypper"]),
]


def detect_package_manager() -> str:
    """Detect the active package manager binary on the host system."""
    for pm_name, binaries in _PACKAGE_MANAGERS:
        for binary in binaries:
            if shutil.which(binary):
                return pm_name
    return "unknown"


def detect_git_status(target_cwd: str) -> Tuple[Optional[str], Optional[bool]]:
    """Discover current git branch name and clean status with strict 1.0s timeout."""
    try:
        # Check if git is available
        if not shutil.which("git"):
            return None, None

        # Check branch name
        branch_proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=target_cwd,
            capture_output=True,
            text=True,
            timeout=1.0,
            check=False,
        )
        if branch_proc.returncode != 0:
            return None, None

        branch_name = branch_proc.stdout.strip()
        if not branch_name or branch_name == "HEAD":
            # Check for detached commit SHA
            sha_proc = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=target_cwd,
                capture_output=True,
                text=True,
                timeout=1.0,
                check=False,
            )
            branch_name = f"detached:{sha_proc.stdout.strip()}" if sha_proc.returncode == 0 else "detached"

        # Check dirty/clean status
        status_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=target_cwd,
            capture_output=True,
            text=True,
            timeout=1.0,
            check=False,
        )
        is_clean = len(status_proc.stdout.strip()) == 0 if status_proc.returncode == 0 else None

        return branch_name, is_clean

    except (subprocess.TimeoutExpired, OSError, Exception):
        return None, None


def is_root_user() -> bool:
    """Determine whether the current process is running with root privileges."""
    try:
        if hasattr(os, "geteuid"):
            return os.geteuid() == 0
    except Exception:
        pass
    return False


def get_current_user() -> str:
    """Retrieve the current login or system username."""
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))


def inspect_system_context(cwd: Optional[str] = None) -> SystemContext:
    """Probe host environment facts returning validated SystemContext per D-01 and CTXT-01.

    Gathers OS distribution, kernel version, hardware architecture, user privileges,
    working directory, active shell, package manager, and git repository state.
    """
    resolved_cwd = str(Path(cwd).resolve()) if cwd else os.getcwd()

    # Detect OS information via distro library with fallback
    distro_name = distro.name(pretty=True) or platform.system()
    distro_version = distro.version() or platform.release()
    distro_family = distro.like() or distro.id() or platform.system().lower()

    # Architecture and kernel
    kernel_release = platform.release() or "unknown"
    arch = platform.machine() or "unknown"

    # User and privileges
    user = get_current_user()
    is_root = is_root_user()

    # Active shell
    default_shell = "/bin/bash" if os.name != "nt" else os.environ.get("COMSPEC", "cmd.exe")
    shell = os.environ.get("SHELL", default_shell)

    # Package manager
    pkg_mgr = detect_package_manager()

    # Git state
    git_branch, git_clean = detect_git_status(resolved_cwd)

    return SystemContext(
        os_name=distro_name,
        os_version=distro_version,
        os_family=distro_family,
        kernel=kernel_release,
        arch=arch,
        cwd=resolved_cwd,
        user=user,
        is_root=is_root,
        shell=shell,
        package_manager=pkg_mgr,
        git_branch=git_branch,
        git_clean=git_clean,
    )
