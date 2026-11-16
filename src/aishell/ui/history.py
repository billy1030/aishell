"""SQLite history adapter for prompt_toolkit."""

import os
from pathlib import Path
from typing import Iterable, Optional
from prompt_toolkit.history import History
from aishell.config.settings import get_settings
from aishell.storage.history import HistoryManager


class SQLiteHistory(History):
    """prompt_toolkit History adapter that stores and retrieves items from SQLite history.db.

    Fulfills REPL-02, D-04, D-11 without creating duplicate disk history files.
    """

    def __init__(
        self,
        history_manager: Optional[HistoryManager] = None,
        db_path: Optional[Path] = None,
        session_id: Optional[str] = None,
        max_records: int = 1000,
    ) -> None:
        super().__init__()
        if history_manager is not None:
            self.history_manager = history_manager
        else:
            settings = get_settings()
            target_db = db_path or settings.storage.history_db_path
            self.history_manager = HistoryManager(
                db_path=target_db,
                max_records=settings.storage.max_history_records,
            )
        self.session_id = session_id or "repl-session"
        self.max_records = max_records

    def get_strings(self) -> list[str]:
        """Get the strings loaded so far in chronological order (oldest first)."""
        if not self._loaded:
            self._loaded_strings = list(self.load_history_strings())
            self._loaded = True
        return self._loaded_strings[::-1]

    def load_history_strings(self) -> Iterable[str]:
        """Yield past commands from SQLite, most recent items first per prompt_toolkit protocol."""
        try:
            records = self.history_manager.query_history(limit=self.max_records)
            seen_last: Optional[str] = None
            for rec in records:
                cmd = rec.command.strip()
                if cmd and cmd != seen_last:
                    seen_last = cmd
                    yield rec.command
        except Exception:
            # Fallback gracefully if database read fails
            return

    def store_string(self, string: str) -> None:
        """Store newly submitted command line in SQLite history database."""
        text = string.strip()
        if not text:
            return

        try:
            self.history_manager.record_execution(
                session_id=self.session_id,
                command=string,
                cwd=os.getcwd(),
                exit_code=0,
                duration_ms=0.0,
                output=None,
                executed_by="user",
            )
        except Exception:
            # Defensive write failure handling (read-only filesystem, lock timeout)
            pass
