"""Unit tests for SystemContext schema and host context inspector."""

import os
from unittest.mock import MagicMock, patch
import pytest

from aishell.context.inspector import (
    detect_git_status,
    detect_package_manager,
    get_current_user,
    inspect_system_context,
    is_root_user,
)
from aishell.context.schema import SystemContext


def test_system_context_schema():
    """Verify SystemContext Pydantic validation and field defaults."""
    ctx = SystemContext(
        os_name="Ubuntu 24.04.1 LTS",
        os_version="24.04",
        os_family="debian",
        kernel="6.8.0-generic",
        arch="x86_64",
        cwd="/home/user/project",
        user="sysadmin",
        is_root=False,
        shell="/bin/zsh",
        package_manager="apt",
        git_branch="main",
        git_clean=True,
        env_vars={"PATH": "/usr/bin"},
    )
    assert ctx.os_name == "Ubuntu 24.04.1 LTS"
    assert ctx.is_root is False
    assert ctx.package_manager == "apt"
    assert ctx.git_branch == "main"
    assert ctx.git_clean is True


def test_core_os_inspection():
    """Verify inspect_system_context returns valid host attributes without crashing."""
    ctx = inspect_system_context()
    assert isinstance(ctx, SystemContext)
    assert bool(ctx.os_name)
    assert bool(ctx.cwd)
    assert bool(ctx.user)
    assert isinstance(ctx.is_root, bool)
    assert ctx.arch != ""


def test_detect_package_manager_mocking():
    """Verify detect_package_manager identifies package managers in priority order."""
    with patch("shutil.which", side_effect=lambda bin: bin in ("apt-get", "apt")):
        assert detect_package_manager() == "apt"

    with patch("shutil.which", side_effect=lambda bin: bin == "dnf"):
        assert detect_package_manager() == "dnf"

    with patch("shutil.which", side_effect=lambda bin: bin == "pacman"):
        assert detect_package_manager() == "pacman"

    with patch("shutil.which", side_effect=lambda bin: bin == "apk"):
        assert detect_package_manager() == "apk"

    with patch("shutil.which", side_effect=lambda bin: bin == "zypper"):
        assert detect_package_manager() == "zypper"

    with patch("shutil.which", return_value=None):
        assert detect_package_manager() == "unknown"


def test_detect_git_status_in_repo():
    """Verify git branch and clean status discovery in a repository."""
    branch, is_clean = detect_git_status(os.getcwd())
    # Current repository has branch and status
    assert branch is not None
    assert isinstance(is_clean, bool)


def test_detect_git_status_outside_repo(tmp_path):
    """Verify detect_git_status gracefully returns None, None outside git repos."""
    branch, is_clean = detect_git_status(str(tmp_path))
    assert branch is None
    assert is_clean is None


def test_detect_git_status_timeout():
    """Verify timeout in git execution does not crash."""
    with patch("subprocess.run", side_effect=TimeoutError("Timeout")):
        branch, is_clean = detect_git_status(os.getcwd())
        assert branch is None
        assert is_clean is None


def test_root_user_detection():
    """Verify root detection returns boolean and handles missing geteuid."""
    res = is_root_user()
    assert isinstance(res, bool)

    with patch.object(os, "geteuid", create=True, return_value=0):
        assert is_root_user() is True

    with patch.object(os, "geteuid", create=True, return_value=1000):
        assert is_root_user() is False
