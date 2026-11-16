"""Unit tests for storage schema, WAL mode, and history manager."""

import os
import sqlite3
import pytest
from pathlib import Path
from aishell.storage.schema import CREATE_AUDIT_TABLE_SQL, ensure_storage_dir, get_connection, init_db
from aishell.storage.history import CommandRecord, HistoryManager, truncate_output_preview


def test_schema_creation_and_indexes(tmp_path: Path):
    db_file = tmp_path / "aishell" / "history.db"
    init_db(db_file)

    assert db_file.exists()

    with get_connection(db_file) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='command_history';")
        assert cursor.fetchone() is not None

        # Verify indexes exist
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = {row["name"] for row in cursor.fetchall()}
        assert "idx_command_history_timestamp" in indexes
        assert "idx_command_history_session" in indexes
        assert "idx_command_history_command" in indexes


def test_wal_mode_and_busy_timeout(tmp_path: Path):
    db_file = tmp_path / "aishell" / "history.db"
    init_db(db_file)

    with get_connection(db_file) as conn:
        cursor = conn.execute("PRAGMA journal_mode;")
        row = cursor.fetchone()
        assert row[0].lower() == "wal"

        cursor = conn.execute("PRAGMA busy_timeout;")
        row = cursor.fetchone()
        assert int(row[0]) >= 5000


def test_directory_creation_and_permissions(tmp_path: Path):
    target_dir = tmp_path / "nested" / "secure_dir"
    db_file = target_dir / "history.db"

    ensured = ensure_storage_dir(db_file)
    assert ensured.exists()
    assert ensured.is_dir()

    if os.name != "nt" and hasattr(os, "stat"):
        mode = oct(os.stat(ensured).st_mode & 0o777)
        assert mode == "0o700"


def test_output_preview_truncation():
    # Small output is kept untouched
    short_text = "hello world"
    assert truncate_output_preview(short_text, 100, 100) == short_text
    assert truncate_output_preview(None) is None

    # Large output gets truncated
    head = "A" * 2048
    middle = "M" * 5000
    tail = "Z" * 2048
    large_text = head + middle + tail

    truncated = truncate_output_preview(large_text, 2048, 2048)
    assert truncated is not None
    assert truncated.startswith("A" * 2048)
    assert truncated.endswith("Z" * 2048)
    assert "[truncated 5000 bytes]" in truncated


def test_history_record_and_query(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    manager = HistoryManager(db_path=db_file, max_records=100)

    # Insert two records
    id1 = manager.record_execution(
        session_id="session-1",
        command="ls -la",
        cwd="/home/user",
        exit_code=0,
        duration_ms=45.2,
        output="total 0\n",
        executed_by="user",
        timestamp=1000.0,
    )
    id2 = manager.record_execution(
        session_id="session-2",
        command="grep foo bar",
        cwd="/var/log",
        exit_code=1,
        duration_ms=120.0,
        output=None,
        executed_by="ai_proposal",
        timestamp=2000.0,
    )

    assert id1 > 0
    assert id2 > id1
    assert manager.count_records() == 2

    # Query all (ordered by timestamp desc)
    records = manager.query_history()
    assert len(records) == 2
    assert records[0].command == "grep foo bar"
    assert records[0].executed_by == "ai_proposal"
    assert records[1].command == "ls -la"
    assert records[1].executed_by == "user"

    # Query filtered by session
    s1_records = manager.query_history(session_id="session-1")
    assert len(s1_records) == 1
    assert s1_records[0].session_id == "session-1"

    # Query filtered by command
    grep_records = manager.query_history(command_filter="grep")
    assert len(grep_records) == 1
    assert grep_records[0].command == "grep foo bar"


def test_bounded_fifo_pruning(tmp_path: Path):
    db_file = tmp_path / "test_prune.db"
    # Create with max_records = 5
    manager = HistoryManager(db_path=db_file, max_records=5)

    # Insert 8 records with increasing timestamps
    for i in range(8):
        manager.record_execution(
            session_id="s1",
            command=f"echo {i}",
            cwd="/tmp",
            exit_code=0,
            duration_ms=10.0,
            timestamp=100.0 + i,
        )

    # Currently 8 records inserted
    assert manager.count_records() == 8

    # Manually prune to 5
    pruned_count = manager.prune_history(max_records=5)
    assert pruned_count == 3
    assert manager.count_records() == 5

    # Remaining records should be the newest 5 (echo 3 through echo 7)
    remaining = manager.query_history(limit=10)
    assert len(remaining) == 5
    commands = [r.command for r in remaining]
    assert commands == ["echo 7", "echo 6", "echo 5", "echo 4", "echo 3"]

    # Initialize a new HistoryManager on same db with max_records=3
    # Verifies startup pruning
    manager2 = HistoryManager(db_path=db_file, max_records=3)
    assert manager2.count_records() == 3
    commands_after_init = [r.command for r in manager2.query_history()]
    assert commands_after_init == ["echo 7", "echo 6", "echo 5"]
