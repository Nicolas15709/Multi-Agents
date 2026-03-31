"""Tests for database initialization and basic operations."""

import sqlite3
from pathlib import Path

import pytest

from runtime.python.db import Database


def test_database_initialization(temp_db_path):
    """Test that database initialization creates the expected tables."""
    db = Database(temp_db_path)
    db.init()

    # Check that key tables exist
    cursor = db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row["name"] for row in cursor.fetchall()]

    expected_tables = [
        "agent_status",
        "missions",
        "mission_events",
        "tasks",
        "policies",
        "notifications",
        "schema_version",
    ]
    for table in expected_tables:
        assert table in tables

    db.close()


def test_database_connection_closes(temp_db_path):
    """Test that database connection closes properly."""
    db = Database(temp_db_path)
    db.init()
    db.close()

    # After closing, attempting to use the connection should fail
    with pytest.raises(sqlite3.ProgrammingError):
        db.execute("SELECT 1")


def test_database_transactions_commit(temp_db_path):
    """Test that database transactions are committed."""
    db = Database(temp_db_path)
    db.init()

    # Insert test data
    db.execute(
        "INSERT INTO missions (id, title, goal, mode, priority, status, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "test-mission-1",
            "Test Mission",
            "Test goal",
            "test_mode",
            "medium",
            "queued",
            "test",
            "2024-01-01T00:00:00Z",
            "2024-01-01T00:00:00Z",
        ),
    )

    # Query in a new connection to verify commit
    new_conn = sqlite3.connect(temp_db_path)
    new_conn.row_factory = sqlite3.Row
    cursor = new_conn.execute("SELECT * FROM missions WHERE id = ?", ("test-mission-1",))
    row = cursor.fetchone()
    new_conn.close()

    assert row is not None
    assert row["title"] == "Test Mission"

    db.close()
