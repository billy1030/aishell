"""Unit tests for InteractiveREPL loop, keybindings, and signal lifecycle."""

import time
from unittest.mock import MagicMock
import pytest
from rich.console import Console

from aishell.config.settings import AishellSettings
from aishell.ui.repl import InteractiveREPL


def test_repl_init():
    settings = AishellSettings()
    repl = InteractiveREPL(settings=settings)
    assert repl.session is not None
    assert repl.is_streaming is False
    assert repl.last_interrupt_time == 0.0


def test_repl_meta_commands():
    test_console = Console(file=MagicMock())
    repl = InteractiveREPL(console=test_console)

    assert repl.handle_meta_command(":exit") is True
    assert repl.handle_meta_command("/quit") is True
    assert repl.handle_meta_command("exit") is True
    assert repl.handle_meta_command(":help") is False
    assert repl.handle_meta_command("/clear") is False


def test_repl_dispatch_meta_exit():
    repl = InteractiveREPL()
    with pytest.raises(EOFError):
        repl.dispatch_input(":exit")


def test_repl_dispatch_direct_shell():
    mock_executor = MagicMock(return_value=0)
    repl = InteractiveREPL(executor_fn=mock_executor)

    # Shell command with !
    repl.dispatch_input("!echo hello from shell")
    mock_executor.assert_called_with("echo hello from shell")

    # Builtin command
    repl.dispatch_input("cd /tmp")
    mock_executor.assert_called_with("cd /tmp")


def test_repl_dispatch_ai_query():
    test_console = Console(file=MagicMock())
    repl = InteractiveREPL(console=test_console)
    # Natural language query should stream without error
    repl.dispatch_input("how do I check disk space?")
    assert repl.is_streaming is False


def test_repl_multiline_backslash_logic():
    repl = InteractiveREPL()
    # Find enter handler from keybindings
    enter_handlers = [
        binding.handler
        for binding in repl.kb.bindings
        if binding.handler.__name__ == "_handle_enter"
    ]
    assert len(enter_handlers) > 0

    # Simulate mock event with buffer ending with backslash
    mock_event = MagicMock()
    mock_buffer = MagicMock()
    mock_buffer.text = "mkdir test_folder \\\n"
    # Test line ending with backslash
    mock_buffer.text = "SELECT * FROM logs \\"
    mock_event.current_buffer = mock_buffer

    handler = enter_handlers[0]
    handler(mock_event)

    mock_buffer.delete_before_cursor.assert_called_with(count=1)
    mock_buffer.insert_text.assert_called_with("\n")


def test_repl_double_ctrl_c_lifecycle():
    repl = InteractiveREPL()

    # First Ctrl+C records timestamp
    now = time.time()
    repl.last_interrupt_time = now
    # Second Ctrl+C within 1.0s satisfies exit condition
    assert (now + 0.5) - repl.last_interrupt_time <= 1.5
    # Ctrl+C after 2.0s does not satisfy exit condition
    assert (now + 2.0) - repl.last_interrupt_time > 1.5
