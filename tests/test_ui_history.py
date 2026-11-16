"""Unit tests for prompt_toolkit SQLite history adapter."""

from pathlib import Path
import pytest
from aishell.storage.history import HistoryManager
from aishell.ui.history import SQLiteHistory


def test_sqlite_history_load_empty(tmp_path: Path):
    db_file = tmp_path / "empty_history.db"
    manager = HistoryManager(db_path=db_file)
    hist = SQLiteHistory(history_manager=manager)

    loaded = list(hist.load_history_strings())
    assert loaded == []


def test_sqlite_history_load_and_order(tmp_path: Path):
    db_file = tmp_path / "order_history.db"
    manager = HistoryManager(db_path=db_file)

    # Insert items at increasing timestamps
    manager.record_execution("s1", "first cmd", "/tmp", 0, 10.0, timestamp=100.0)
    manager.record_execution("s1", "second cmd", "/tmp", 0, 10.0, timestamp=200.0)
    manager.record_execution("s1", "third cmd", "/tmp", 0, 10.0, timestamp=300.0)

    hist = SQLiteHistory(history_manager=manager)
    # load_history_strings should yield most recent items first
    loaded = list(hist.load_history_strings())
    assert loaded == ["third cmd", "second cmd", "first cmd"]

    # get_strings() returns oldest first per prompt_toolkit contract
    hist_strings = hist.get_strings()
    assert hist_strings == ["first cmd", "second cmd", "third cmd"]


def test_sqlite_history_store_string(tmp_path: Path):
    db_file = tmp_path / "store_history.db"
    manager = HistoryManager(db_path=db_file)
    hist = SQLiteHistory(history_manager=manager, session_id="test-sess")

    # Store via store_string
    hist.store_string("new command to store")

    records = manager.query_history()
    assert len(records) == 1
    assert records[0].command == "new command to store"
    assert records[0].session_id == "test-sess"

    # Empty string should not be stored
    hist.store_string("   ")
    assert len(manager.query_history()) == 1


def test_sqlite_history_append_string(tmp_path: Path):
    db_file = tmp_path / "append_history.db"
    manager = HistoryManager(db_path=db_file)
    hist = SQLiteHistory(history_manager=manager)

    hist.append_string("appended command")
    assert "appended command" in hist.get_strings()

    records = manager.query_history()
    assert len(records) == 1
    assert records[0].command == "appended command"
