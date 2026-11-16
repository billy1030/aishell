"""Circular in-memory ring buffer for command execution output."""

from typing import List, Union


class CircularRingBuffer:
    """Bounded ring buffer capping captured text to rolling max_bytes and max_lines."""

    def __init__(self, max_bytes: int = 50 * 1024, max_lines: int = 1000) -> None:
        self.max_bytes = max_bytes
        self.max_lines = max_lines
        self._buffer: List[str] = []
        self._current_bytes = 0

    def append(self, chunk: Union[str, bytes]) -> None:
        """Append text or bytes chunk into buffer, trimming oldest data if bounds exceeded."""
        if isinstance(chunk, bytes):
            text = chunk.decode("utf-8", errors="replace")
        else:
            text = chunk

        if not text:
            return

        # Split new text preserving line structure
        new_lines = text.splitlines(keepends=True)
        if not new_lines:
            return

        for line in new_lines:
            line_bytes = len(line.encode("utf-8", errors="replace"))
            self._buffer.append(line)
            self._current_bytes += line_bytes

        self._enforce_bounds()

    def _enforce_bounds(self) -> None:
        """Enforce max_lines and max_bytes by discarding oldest lines."""
        # Trim by max_lines first
        while len(self._buffer) > self.max_lines:
            popped = self._buffer.pop(0)
            self._current_bytes -= len(popped.encode("utf-8", errors="replace"))

        # Trim by max_bytes
        while self._buffer and self._current_bytes > self.max_bytes:
            popped = self._buffer.pop(0)
            self._current_bytes -= len(popped.encode("utf-8", errors="replace"))

        if self._current_bytes < 0:
            self._current_bytes = 0

    def get_content(self) -> str:
        """Return the entire retained output as a single string."""
        return "".join(self._buffer)

    def get_lines(self) -> List[str]:
        """Return list of retained lines."""
        return list(self._buffer)

    def clear(self) -> None:
        """Reset the buffer."""
        self._buffer.clear()
        self._current_bytes = 0

    @property
    def current_bytes(self) -> int:
        """Current byte size in buffer."""
        return self._current_bytes

    @property
    def line_count(self) -> int:
        """Number of lines currently in buffer."""
        return len(self._buffer)
