"""Managed pseudo-terminal (PTY) runner and execution orchestrator.

Implements dual-mode execution (PTY live streaming per D-01), process group isolation
and SIGINT routing per D-02, circular ring buffer output capture per D-03,
terminal resize propagation per D-04, and defensive termios restoration per Pitfall 2.
Includes a fallback runner for non-POSIX environments (e.g. Windows).
"""

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional

from aishell.execution.ring_buffer import CircularRingBuffer

# Detect POSIX PTY availability
IS_POSIX = os.name != "nt" and sys.platform != "win32"
try:
    import pty
    import termios
    import tty
    import fcntl
    import struct
    import select
    HAS_PTY = True
except ImportError:
    HAS_PTY = False


@dataclass
class ExecutionResult:
    """Result of a command execution."""

    exit_code: int
    duration_ms: float
    output: str
    timed_out: bool = False


def _set_terminal_winsize(slave_fd: int) -> None:
    """Synchronize host terminal dimensions to slave PTY per D-04."""
    if not HAS_PTY:
        return
    try:
        # Query host terminal size from stdin/stdout if available
        for fd in (sys.stdin.fileno(), sys.stdout.fileno()):
            try:
                winsize = fcntl.ioctl(fd, termios.TIOCGWINSZ, b"\x00" * 8)
                fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
                return
            except (OSError, ValueError):
                continue
    except Exception:
        pass


def _run_posix_pty(
    command: str,
    cwd: Optional[str] = None,
    timeout: float = 300.0,
    echo_to_terminal: bool = True,
    ring_buffer: Optional[CircularRingBuffer] = None,
) -> ExecutionResult:
    """Execute command in a managed PTY on POSIX systems."""
    buffer = ring_buffer or CircularRingBuffer()
    master_fd, slave_fd = pty.openpty()
    _set_terminal_winsize(slave_fd)

    start_time = time.perf_counter()
    proc = None
    old_sigint = None
    old_sigwinch = None
    old_term_attrs = None
    stdin_fd = None
    is_interactive_terminal = False

    try:
        if sys.stdin.isatty():
            stdin_fd = sys.stdin.fileno()
            try:
                old_term_attrs = termios.tcgetattr(stdin_fd)
                is_interactive_terminal = True
            except (termios.error, OSError):
                is_interactive_terminal = False

        # Launch process with slave_fd as stdio, isolated in its own process group (os.setsid) per D-02
        proc = subprocess.Popen(
            command,
            shell=True,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=cwd,
            close_fds=True,
            preexec_fn=os.setsid,
        )

        # Close slave_fd in parent process so EOF on master_fd is detected when child exits
        os.close(slave_fd)
        slave_fd = -1

        child_pgid = proc.pid

        # Forward SIGINT (Ctrl+C) to child process group without terminating aishell per D-02
        def handle_sigint(signum, frame):
            try:
                if proc and proc.poll() is None:
                    os.killpg(child_pgid, signal.SIGINT)
            except OSError:
                pass

        # Trap SIGWINCH to update slave PTY dimensions dynamically per D-04
        def handle_sigwinch(signum, frame):
            try:
                if master_fd >= 0:
                    _set_terminal_winsize(master_fd)
            except Exception:
                pass

        old_sigint = signal.signal(signal.SIGINT, handle_sigint)
        if hasattr(signal, "SIGWINCH"):
            old_sigwinch = signal.signal(signal.SIGWINCH, handle_sigwinch)

        # Put stdin into raw mode for interactive bidirectional PTY forwarding (bash, vim, sudo, top)
        forward_stdin = bool(is_interactive_terminal and echo_to_terminal and stdin_fd is not None)
        if forward_stdin:
            try:
                tty.setraw(stdin_fd)
            except (termios.error, OSError):
                forward_stdin = False

        # Polling loop for bidirectional PTY I/O streaming with timeout
        timed_out = False
        deadline = start_time + timeout
        watch_fds = [master_fd, stdin_fd] if forward_stdin else [master_fd]

        while True:
            remaining_time = deadline - time.perf_counter()
            if remaining_time <= 0:
                timed_out = True
                try:
                    os.killpg(child_pgid, signal.SIGKILL)
                except OSError:
                    pass
                break

            # Wait for master_fd output or stdin_fd user input
            r, _, _ = select.select(watch_fds, [], [], min(0.1, remaining_time))
            if forward_stdin and stdin_fd in r:
                try:
                    user_data = os.read(stdin_fd, 1024)
                    if user_data:
                        os.write(master_fd, user_data)
                except OSError:
                    forward_stdin = False
                    watch_fds = [master_fd]

            if master_fd in r:
                try:
                    data = os.read(master_fd, 4096)
                    if not data:
                        break  # EOF reached
                    if echo_to_terminal:
                        sys.stdout.buffer.write(data)
                        sys.stdout.buffer.flush()
                    buffer.append(data)
                except OSError:
                    # Input/output error typically indicates child closed slave PTY
                    break

            if proc.poll() is not None:
                # Read any remaining bytes left in the buffer before exiting
                while True:
                    r, _, _ = select.select([master_fd], [], [], 0.05)
                    if not r:
                        break
                    try:
                        data = os.read(master_fd, 4096)
                        if not data:
                            break
                        if echo_to_terminal:
                            sys.stdout.buffer.write(data)
                            sys.stdout.buffer.flush()
                        buffer.append(data)
                    except OSError:
                        break
                break

        exit_code = proc.wait() if proc else 1
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return ExecutionResult(
            exit_code=exit_code if not timed_out else 124,
            duration_ms=duration_ms,
            output=buffer.get_content(),
            timed_out=timed_out,
        )

    finally:
        # Defensive cleanup: restore terminal modes per Pitfall 2
        if old_term_attrs is not None and stdin_fd is not None:
            try:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_term_attrs)
            except (termios.error, OSError):
                pass

        if old_sigint is not None:
            signal.signal(signal.SIGINT, old_sigint)
        if old_sigwinch is not None and hasattr(signal, "SIGWINCH"):
            signal.signal(signal.SIGWINCH, old_sigwinch)

        if slave_fd >= 0:
            try:
                os.close(slave_fd)
            except OSError:
                pass
        try:
            os.close(master_fd)
        except OSError:
            pass


def _run_subprocess_fallback(
    command: str,
    cwd: Optional[str] = None,
    timeout: float = 300.0,
    echo_to_terminal: bool = True,
    ring_buffer: Optional[CircularRingBuffer] = None,
) -> ExecutionResult:
    """Fallback runner for environments without PTY (e.g. Windows)."""
    buffer = ring_buffer or CircularRingBuffer()
    start_time = time.perf_counter()
    timed_out = False

    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            bufsize=0,
        )

        deadline = start_time + timeout

        if proc.stdout:
            while True:
                remaining_time = deadline - time.perf_counter()
                if remaining_time <= 0:
                    timed_out = True
                    proc.kill()
                    break

                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    time.sleep(0.01)
                    continue

                if echo_to_terminal:
                    sys.stdout.buffer.write(line)
                    sys.stdout.buffer.flush()
                buffer.append(line)

        exit_code = proc.wait()
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return ExecutionResult(
            exit_code=exit_code if not timed_out else 124,
            duration_ms=duration_ms,
            output=buffer.get_content(),
            timed_out=timed_out,
        )

    except subprocess.TimeoutExpired:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return ExecutionResult(exit_code=124, duration_ms=duration_ms, output=buffer.get_content(), timed_out=True)
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return ExecutionResult(exit_code=1, duration_ms=duration_ms, output=str(e), timed_out=False)


def run_in_pty(
    command: str,
    cwd: Optional[str] = None,
    timeout: float = 300.0,
    echo_to_terminal: bool = True,
    ring_buffer: Optional[CircularRingBuffer] = None,
) -> ExecutionResult:
    """Run command in a managed PTY (or fallback runner on non-POSIX)."""
    if IS_POSIX and HAS_PTY:
        return _run_posix_pty(
            command=command,
            cwd=cwd,
            timeout=timeout,
            echo_to_terminal=echo_to_terminal,
            ring_buffer=ring_buffer,
        )
    else:
        return _run_subprocess_fallback(
            command=command,
            cwd=cwd,
            timeout=timeout,
            echo_to_terminal=echo_to_terminal,
            ring_buffer=ring_buffer,
        )
