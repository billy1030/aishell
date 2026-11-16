"""Unit tests for shell builtin interception and state synchronization."""

import os
from pathlib import Path
import pytest
from aishell.execution.builtins import (
    handle_cd,
    handle_export,
    handle_unset,
    is_builtin_command,
    sync_compound_cwd,
    try_execute_builtin,
)


def test_is_builtin_command():
    assert is_builtin_command("cd /tmp") is True
    assert is_builtin_command("export FOO=bar") is True
    assert is_builtin_command("unset FOO") is True
    assert is_builtin_command("ls -la") is False
    assert is_builtin_command("git status") is False
    assert is_builtin_command("") is False


def test_handle_cd_navigation(tmp_path: Path):
    initial_cwd = os.getcwd()
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()

    try:
        # Navigate to sub_dir
        code, out = handle_cd([str(sub_dir)])
        assert code == 0
        assert Path(os.getcwd()).resolve() == sub_dir.resolve()
        assert Path(os.environ["OLDPWD"]).resolve() == Path(initial_cwd).resolve()
        assert Path(os.environ["PWD"]).resolve() == sub_dir.resolve()

        # Navigate using `cd -`
        code, out = handle_cd(["-"])
        assert code == 0
        assert Path(os.getcwd()).resolve() == Path(initial_cwd).resolve()
        assert Path(os.environ["OLDPWD"]).resolve() == sub_dir.resolve()
        assert str(Path(initial_cwd).resolve()) in out

        # Navigate to home using `cd ~`
        home_path = Path.home().resolve()
        code, _ = handle_cd(["~"])
        assert code == 0
        assert Path(os.getcwd()).resolve() == home_path

        # Navigate with no args defaults to home
        os.chdir(sub_dir)
        code, _ = handle_cd([])
        assert code == 0
        assert Path(os.getcwd()).resolve() == home_path

        # Invalid directory
        code, err = handle_cd(["non_existent_directory_xyz"])
        assert code == 1
        assert "no such file or directory" in err.lower()
    finally:
        os.chdir(initial_cwd)


def test_handle_export_and_unset():
    # Test setting variable
    code, _ = handle_export(["TEST_AISHELL_VAR=hello_world"])
    assert code == 0
    assert os.environ.get("TEST_AISHELL_VAR") == "hello_world"

    # Test setting with quotes
    code, _ = handle_export(['TEST_QUOTED="spaced value"'])
    assert code == 0
    assert os.environ.get("TEST_QUOTED") == "spaced value"

    # Test bare export
    code, listing = handle_export([])
    assert code == 0
    assert 'TEST_AISHELL_VAR="hello_world"' in listing

    # Test unset
    code, _ = handle_unset(["TEST_AISHELL_VAR", "TEST_QUOTED"])
    assert code == 0
    assert "TEST_AISHELL_VAR" not in os.environ
    assert "TEST_QUOTED" not in os.environ

    # Unsetting non-existent key does not raise error
    code, _ = handle_unset(["NON_EXISTENT_VAR_123"])
    assert code == 0


def test_try_execute_builtin(tmp_path: Path):
    initial_cwd = os.getcwd()
    try:
        # Builtin execution
        res = try_execute_builtin(f"cd {tmp_path}")
        assert res is not None
        code, _ = res
        assert code == 0
        assert Path(os.getcwd()).resolve() == tmp_path.resolve()

        # Non-builtin returns None
        assert try_execute_builtin("ls -la") is None
    finally:
        os.chdir(initial_cwd)


def test_sync_compound_cwd(tmp_path: Path):
    initial_cwd = os.getcwd()
    sub_dir = tmp_path / "compound_test"
    sub_dir.mkdir()

    try:
        # Compound command with exit code 0
        sync_compound_cwd(f"echo test && cd {sub_dir}", exit_code=0)
        assert Path(os.getcwd()).resolve() == sub_dir.resolve()

        # Reset cwd
        os.chdir(tmp_path)

        # Compound command with non-zero exit code should NOT sync cwd
        sync_compound_cwd(f"failing_cmd && cd {sub_dir}", exit_code=1)
        assert Path(os.getcwd()).resolve() == tmp_path.resolve()
    finally:
        os.chdir(initial_cwd)
