"""SQLite audit database schema and connection management."""

import os
import sqlite3
from pathlib import Path

CREATE_AUDIT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS command_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    command TEXT NOT NULL,
    cwd TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    duration_ms REAL NOT NULL,
    output_preview TEXT,
    executed_by TEXT NOT NULL DEFAULT 'user'
);

CREATE INDEX IF NOT EXISTS idx_command_history_timestamp
ON command_history(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_command_history_session
ON command_history(session_id);

CREATE INDEX IF NOT EXISTS idx_command_history_command
ON command_history(command);
"""


def ensure_storage_dir(db_path: Path) -> Path:
    """Ensure parent directory for history database exists with 0700 permissions."""
    parent_dir = db_path.parent
    if not parent_dir.exists():
        parent_dir.mkdir(parents=True, exist_ok=True)
        try:
            if hasattr(os, "chmod") and os.name != "nt":
                os.chmod(parent_dir, 0o700)
        except OSError:
            pass
    return parent_dir


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Open SQLite connection with WAL mode and busy timeout configured.

    Enforces 0700 permissions on the parent directory per D-10 and D-15.
    Enables Write-Ahead Logging (WAL) and 5000ms busy timeout per D-12.
    """
    ensure_storage_dir(db_path)
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row

    # Enable WAL mode and busy timeout for concurrent process access
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;")

    return conn


def init_db(db_path: Path) -> None:
    """Initialize database tables and indexes idempotently."""
    with get_connection(db_path) as conn:
        conn.executescript(CREATE_AUDIT_TABLE_SQL)
        conn.commit()
