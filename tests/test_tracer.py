"""Tests for CLI tracer execution and end-to-end integration."""

import os
import sys
from pathlib import Path
from typer.testing import CliRunner
from aishell.cli import app
from aishell import __version__
from aishell.config.settings import get_settings
from aishell.storage.history import HistoryManager

runner = CliRunner()


def test_cli_version():
    """Verify that --version outputs the correct version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_exec_success(tmp_path: Path, monkeypatch):
    """Verify that a successful command executes with exit code 0 and logs to history."""
    db_file = tmp_path / "test_cli_history.db"
    monkeypatch.setenv("AISHELL_STORAGE__HISTORY_DB_PATH", str(db_file))

    cmd = f'{sys.executable} -c "print(\'tracer test output\')"'
    result = runner.invoke(app, ["exec", cmd])
    assert result.exit_code == 0

    history = HistoryManager(db_path=db_file)
    records = history.query_history()
    assert len(records) >= 1
    assert records[0].exit_code == 0
    assert "tracer test output" in (records[0].output_preview or "")


def test_cli_exec_failure(tmp_path: Path, monkeypatch):
    """Verify that a failing command returns a non-zero exit code and logs to history."""
    db_file = tmp_path / "test_cli_history_fail.db"
    monkeypatch.setenv("AISHELL_STORAGE__HISTORY_DB_PATH", str(db_file))

    cmd = f'{sys.executable} -c "import sys; sys.exit(42)"'
    result = runner.invoke(app, ["exec", cmd])
    assert result.exit_code == 42

    history = HistoryManager(db_path=db_file)
    records = history.query_history()
    assert len(records) >= 1
    assert records[0].exit_code == 42


def test_cli_run_alias(tmp_path: Path, monkeypatch):
    """Verify that the 'run' command alias works identically to 'exec'."""
    db_file = tmp_path / "test_cli_alias.db"
    monkeypatch.setenv("AISHELL_STORAGE__HISTORY_DB_PATH", str(db_file))

    cmd = f'{sys.executable} -c "print(\'alias run output\')"'
    result = runner.invoke(app, ["run", cmd])
    assert result.exit_code == 0

    history = HistoryManager(db_path=db_file)
    records = history.query_history()
    assert len(records) >= 1
    assert "alias run output" in (records[0].output_preview or "")


def test_cli_exec_builtin_cd(tmp_path: Path, monkeypatch):
    """Verify that 'aishell exec cd <dir>' executes builtin and persists history."""
    db_file = tmp_path / "test_cli_cd.db"
    monkeypatch.setenv("AISHELL_STORAGE__HISTORY_DB_PATH", str(db_file))

    target_dir = tmp_path / "nav_test"
    target_dir.mkdir()

    result = runner.invoke(app, ["exec", f"cd {target_dir}"])
    assert result.exit_code == 0

    history = HistoryManager(db_path=db_file)
    records = history.query_history()
    assert len(records) >= 1
    assert f"cd {target_dir}" in records[0].command
