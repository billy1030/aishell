"""Unit tests for managed execution runner and ring buffer."""

import sys
import pytest
from pathlib import Path
from aishell.execution.ring_buffer import CircularRingBuffer
from aishell.execution.pty_runner import run_in_pty, ExecutionResult


def test_ring_buffer_basic_append():
    buf = CircularRingBuffer(max_bytes=1000, max_lines=10)
    buf.append("line 1\n")
    buf.append(b"line 2\n")

    assert buf.line_count == 2
    assert "line 1\nline 2\n" == buf.get_content()
    assert buf.get_lines() == ["line 1\n", "line 2\n"]

    buf.clear()
    assert buf.line_count == 0
    assert buf.get_content() == ""


def test_ring_buffer_line_capping():
    # Capped at 3 lines
    buf = CircularRingBuffer(max_bytes=10000, max_lines=3)
    for i in range(5):
        buf.append(f"line {i}\n")

    assert buf.line_count == 3
    assert buf.get_lines() == ["line 2\n", "line 3\n", "line 4\n"]


def test_ring_buffer_byte_capping():
    # Capped at 20 bytes
    buf = CircularRingBuffer(max_bytes=20, max_lines=100)
    # Each line is 10 bytes: '123456789\n'
    buf.append("123456789\n")
    buf.append("abcdefghi\n")
    buf.append("ABCDEFGHI\n")

    # Should retain at most 20 bytes (the last 2 lines)
    assert buf.current_bytes <= 20
    assert "ABCDEFGHI\n" in buf.get_content()
    assert "123456789\n" not in buf.get_content()


def test_run_in_pty_success():
    cmd = f'{sys.executable} -c "print(\'pty test execution\')"'
    res = run_in_pty(cmd, echo_to_terminal=False)

    assert isinstance(res, ExecutionResult)
    assert res.exit_code == 0
    assert "pty test execution" in res.output
    assert res.duration_ms > 0
    assert not res.timed_out


def test_run_in_pty_failure():
    cmd = f'{sys.executable} -c "import sys; print(\'failure msg\'); sys.exit(7)"'
    res = run_in_pty(cmd, echo_to_terminal=False)

    assert res.exit_code == 7
    assert "failure msg" in res.output
    assert not res.timed_out


def test_run_in_pty_timeout():
    cmd = f'{sys.executable} -c "import time; time.sleep(5)"'
    res = run_in_pty(cmd, timeout=0.2, echo_to_terminal=False)

    assert res.timed_out is True
    assert res.exit_code == 124


def test_run_in_pty_cwd(tmp_path: Path):
    marker = tmp_path / "marker.txt"
    marker.write_text("found marker", encoding="utf-8")

    cmd = f'{sys.executable} -c "import os; print(os.path.exists(\'marker.txt\'))"'
    res = run_in_pty(cmd, cwd=str(tmp_path), echo_to_terminal=False)

    assert res.exit_code == 0
    assert "True" in res.output
