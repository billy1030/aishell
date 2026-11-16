"""Unit and integration tests for CLI --context inspection option."""

from typer.testing import CliRunner
from aishell.cli import app

runner = CliRunner()


def test_cli_context_flag():
    """Verify aishell --context prints host system facts and sanitized environment variables."""
    result = runner.invoke(app, ["--context"])
    assert result.exit_code == 0
    assert "aishell System Context" in result.output
    assert "Host System Facts" in result.output
    assert "OS Distribution" in result.output
    assert "Kernel & Arch" in result.output
    assert "User & Privileges" in result.output
    assert "Working Directory" in result.output
    assert "Package Manager" in result.output
    assert "Sanitized Environment Variables" in result.output

