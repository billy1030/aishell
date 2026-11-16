"""Unit tests for CLI one-shot execution and stdin piping."""

from io import BytesIO, StringIO
import sys
import pytest
from typer.testing import CliRunner
from aishell.cli import app, MAX_STDIN_BYTES
from aishell import __version__

runner = CliRunner()


def test_cli_oneshot_command_flag():
    """Verify aishell -c 'prompt' executes one-shot query."""
    result = runner.invoke(app, ["-c", "how do I find files"])
    assert result.exit_code == 0
    assert "how do I find files" in result.output


def test_cli_oneshot_bare_positional():
    """Verify aishell 'prompt' executes one-shot query."""
    result = runner.invoke(app, ["explain nginx logs"])
    assert result.exit_code == 0
    assert "explain nginx logs" in result.output


def test_cli_oneshot_piped_stdin():
    """Verify piped stdin is ingested when no arguments passed."""
    result = runner.invoke(app, [], input="error: connection refused")
    assert result.exit_code == 0
    assert "error: connection refused" in result.output


def test_cli_oneshot_combined_pipe_and_query():
    """Verify piped stdin and query argument are combined."""
    result = runner.invoke(app, ["diagnose failure"], input="server traceback info")
    assert result.exit_code == 0
    assert "server traceback info" in result.output
    assert "diagnose failure" in result.output


def test_cli_oneshot_oversized_stdin(monkeypatch):
    """Verify piped stdin exceeding 512KB is truncated with a warning."""
    # Generate 600KB of input
    oversized_data = "X" * (600 * 1024)
    result = runner.invoke(app, ["summarize"], input=oversized_data)
    assert result.exit_code == 0
    assert "Warning" in result.output or "truncated" in result.output


def test_subcommands_remain_functional():
    """Verify subcommands like exec and --version continue working seamlessly."""
    ver_res = runner.invoke(app, ["--version"])
    assert ver_res.exit_code == 0
    assert __version__ in ver_res.output

    exec_res = runner.invoke(app, ["exec", "echo subcmd_test"])
    assert exec_res.exit_code == 0
