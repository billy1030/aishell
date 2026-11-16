"""Command execution audit history manager."""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from aishell.config.settings import get_default_history_db_path
from aishell.storage.schema import get_connection, init_db


@dataclass
class CommandRecord:
    """Execution audit record."""

    id: Optional[int]
    session_id: str
    timestamp: float
    command: str
    cwd: str
    exit_code: int
    duration_ms: float
    output_preview: Optional[str]
    executed_by: str = "user"


def truncate_output_preview(output: Optional[str], head_bytes: int = 2048, tail_bytes: int = 2048) -> Optional[str]:
    """Truncate output preview to first and last N bytes if large."""
    if output is None:
        return None
    raw_bytes = output.encode("utf-8", errors="replace")
    total_bytes = len(raw_bytes)
    max_bytes = head_bytes + tail_bytes

    if total_bytes <= max_bytes:
        return output

    head = raw_bytes[:head_bytes].decode("utf-8", errors="replace")
    tail = raw_bytes[-tail_bytes:].decode("utf-8", errors="replace")
    skipped_bytes = total_bytes - max_bytes
    return f"{head}\n\n... [truncated {skipped_bytes} bytes] ...\n\n{tail}"


class HistoryManager:
    """Manages command audit history persistence, querying, and FIFO retention."""

    def __init__(self, db_path: Optional[Path] = None, max_records: int = 10000) -> None:
        self.db_path = db_path or get_default_history_db_path()
        self.max_records = max_records
        init_db(self.db_path)
        self.prune_history(self.max_records)

    def record_execution(
        self,
        session_id: str,
        command: str,
        cwd: str,
        exit_code: int,
        duration_ms: float,
        output: Optional[str] = None,
        executed_by: str = "user",
        timestamp: Optional[float] = None,
    ) -> int:
        """Insert an execution audit record and return the inserted row ID."""
        ts = timestamp if timestamp is not None else time.time()
        preview = truncate_output_preview(output)

        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO command_history (
                    session_id, timestamp, command, cwd,
                    exit_code, duration_ms, output_preview, executed_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    session_id,
                    ts,
                    command,
                    cwd,
                    exit_code,
                    duration_ms,
                    preview,
                    executed_by,
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def query_history(
        self,
        limit: int = 50,
        session_id: Optional[str] = None,
        command_filter: Optional[str] = None,
    ) -> List[CommandRecord]:
        """Query execution history ordered by timestamp descending."""
        query = "SELECT id, session_id, timestamp, command, cwd, exit_code, duration_ms, output_preview, executed_by FROM command_history"
        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if command_filter:
            conditions.append("command LIKE ?")
            params.append(f"%{command_filter}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with get_connection(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                CommandRecord(
                    id=row["id"],
                    session_id=row["session_id"],
                    timestamp=row["timestamp"],
                    command=row["command"],
                    cwd=row["cwd"],
                    exit_code=row["exit_code"],
                    duration_ms=row["duration_ms"],
                    output_preview=row["output_preview"],
                    executed_by=row["executed_by"],
                )
                for row in rows
            ]

    def count_records(self) -> int:
        """Return total number of command records stored."""
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM command_history").fetchone()
            return int(row["total"]) if row else 0

    def prune_history(self, max_records: int) -> int:
        """Prune oldest records when total count exceeds max_records (FIFO)."""
        if max_records <= 0:
            return 0

        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM command_history").fetchone()
            total = int(row["total"]) if row else 0

            if total <= max_records:
                return 0

            to_delete = total - max_records
            cursor = conn.execute(
                """
                DELETE FROM command_history
                WHERE id IN (
                    SELECT id FROM command_history
                    ORDER BY timestamp ASC
                    LIMIT ?
                );
                """,
                (to_delete,),
            )
            conn.commit()
            return cursor.rowcount
