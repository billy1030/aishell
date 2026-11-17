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


def test_repl_direct_shell_vs_ai_wakeup():
    mock_executor = MagicMock(return_value=0)
    mock_provider = MagicMock()
    mock_provider.name = "minimax"
    mock_provider.model = "MiniMax-M3.1-Flash"

    async def fake_stream(_messages, *args, **kwargs):
        yield "AI response"

    mock_provider.stream_chat = fake_stream

    test_console = Console(file=MagicMock())
    repl = InteractiveREPL(
        console=test_console,
        executor_fn=mock_executor,
        provider=mock_provider,
    )

    # Common shell commands execute directly without waking AI
    repl.dispatch_input("ls")
    mock_executor.assert_called_with("ls")

    repl.dispatch_input("df -h")
    mock_executor.assert_called_with("df -h")

    repl.dispatch_input("ps aux")
    mock_executor.assert_called_with("ps aux")

    repl.dispatch_input("bash")
    mock_executor.assert_called_with("bash")

    repl.dispatch_input("./deploy.sh")
    mock_executor.assert_called_with("./deploy.sh")

    repl.dispatch_input("FOO=bar env")
    mock_executor.assert_called_with("FOO=bar env")

    repl.dispatch_input("for i in 1 2; do echo $i; done")
    mock_executor.assert_called_with("for i in 1 2; do echo $i; done")

    # Wake-up triggers route to AI instead of shell executor
    mock_executor.reset_mock()
    repl.dispatch_input("hi, how do I check ports?")
    mock_executor.assert_not_called()

    repl.dispatch_input("please show memory usage")
    mock_executor.assert_not_called()

    repl.dispatch_input("ais ls")
    mock_executor.assert_not_called()
