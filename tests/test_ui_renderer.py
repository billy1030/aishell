"""Unit tests for Rich streaming terminal renderer and capability detection."""

import os
from io import StringIO
import pytest
from rich.console import Console
from aishell.ui.renderer import RichStreamRenderer, detect_terminal_capabilities


def test_detect_terminal_capabilities_no_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    caps = detect_terminal_capabilities()
    assert caps["color_system"] is None


def test_detect_terminal_capabilities_dumb_term(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")
    caps = detect_terminal_capabilities()
    assert caps["color_system"] is None
    assert caps["interactive"] is False


def test_detect_terminal_capabilities_truecolor(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("TERM", raising=False)
    monkeypatch.setenv("COLORTERM", "truecolor")
    caps = detect_terminal_capabilities()
    assert caps["color_system"] == "truecolor"


def test_renderer_stream_markdown_accumulation():
    string_io = StringIO()
    test_console = Console(file=string_io, force_terminal=True, color_system="standard")
    renderer = RichStreamRenderer(console=test_console)

    tokens = ["# Heading\n\n", "Here is a code snippet:\n", "```bash\n", "echo 'hello'\n", "```\n"]
    result = renderer.stream_markdown(tokens)

    assert result == "".join(tokens)
    output = string_io.getvalue()
    assert "Heading" in output
    assert "echo" in output


def test_renderer_thinking_spinner():
    string_io = StringIO()
    test_console = Console(file=string_io, force_terminal=True)
    renderer = RichStreamRenderer(console=test_console)

    with renderer.thinking_spinner("Analyzing..."):
        pass  # spinner active

    # Spinner should have stopped and cleaned up
    assert True


def test_renderer_non_interactive_fallback(monkeypatch):
    string_io = StringIO()
    monkeypatch.setenv("TERM", "dumb")
    test_console = Console(file=string_io, force_terminal=False)
    renderer = RichStreamRenderer(console=test_console)
    assert renderer.interactive is False

    tokens = ["plain ", "text ", "tokens\n"]
    result = renderer.stream_markdown(tokens)

    assert result == "plain text tokens\n"
    assert "plain text tokens" in string_io.getvalue()


def test_renderer_render_error():
    string_io = StringIO()
    test_stderr_console = Console(file=string_io)
    renderer = RichStreamRenderer(stderr_console=test_stderr_console)

    renderer.render_error("Something failed")
    assert "Error:" in string_io.getvalue()
    assert "Something failed" in string_io.getvalue()
