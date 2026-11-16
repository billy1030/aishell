"""Tests for CLI tracer execution."""

from typer.testing import CliRunner
from aishell.cli import app
from aishell import __version__

runner = CliRunner()


def test_cli_version():
    """Verify that --version outputs the correct version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_exec_success():
    """Verify that a successful command executes with exit code 0."""
    result = runner.invoke(app, ["exec", "python -c \"print('tracer test output')\""])
    assert result.exit_code == 0


def test_cli_exec_failure():
    """Verify that a failing command returns a non-zero exit code."""
    result = runner.invoke(app, ["exec", "python -c \"import sys; sys.exit(42)\""])
    assert result.exit_code == 42

