"""
db.py — Unified database adapter.

Auto-detects backend based on env vars:
  - DATABASE_URL set  → PostgreSQL via psycopg2 (Supabase)
  - DATABASE_URL unset → SQLite local fallback (dev/offline mode)

The public interface (execute / fetchall / fetchone / close / init) is
identical for both backends so all repository code works unchanged.
"""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from .storage import ensure_parent
except ImportError:
    from storage import ensure_parent

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"

# ── Placeholder translation: SQLite uses ? → PostgreSQL uses %s ──────────────

def _to_pg(sql: str) -> str:
    """Replace SQLite-style ? placeholders with PostgreSQL %s."""
    return re.sub(r"\?", "%s", sql)


# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL backend (Supabase)
# ─────────────────────────────────────────────────────────────────────────────

class _PostgresDatabase:
    """psycopg2-backed database — connects to Supabase PostgreSQL."""

    def __init__(self, database_url: str) -> None:
        import psycopg2
        import psycopg2.extras
        self._url = database_url
        self.conn = psycopg2.connect(database_url)
        self.conn.autocommit = False
        self._cursor_factory = psycopg2.extras.RealDictCursor

    def init(self) -> None:
        """Schema is managed via Supabase migrations — nothing to do here."""
        pass

    def execute(self, sql: str, params: Iterable[Any] = ()) -> Any:
        sql = _to_pg(sql)
        with self.conn.cursor(cursor_factory=self._cursor_factory) as cur:
            cur.execute(sql, tuple(params))
            self.conn.commit()
            return cur

    def fetchall(self, sql: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
        sql = _to_pg(sql)
        with self.conn.cursor(cursor_factory=self._cursor_factory) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            return [dict(row) for row in rows] if rows else []

    def fetchone(self, sql: str, params: Iterable[Any] = ()) -> Optional[Dict[str, Any]]:
        sql = _to_pg(sql)
        with self.conn.cursor(cursor_factory=self._cursor_factory) as cur:
            cur.execute(sql, tuple(params))
            row = cur.fetchone()
            return dict(row) if row else None

    def close(self) -> None:
        if getattr(self, "conn", None) is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# SQLite backend (local fallback)
# ─────────────────────────────────────────────────────────────────────────────

class _SQLiteDatabase:
    """sqlite3-backed database — local fallback when no DATABASE_URL set."""

    def __init__(self, db_path: str) -> None:
        ensure_parent(db_path)
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def init(self) -> None:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        self.conn.executescript(schema)
        self._ensure_column("agent_hire_requests", "metadata_json", "TEXT")
        self._ensure_column("mission_controls", "action_budgets_json", "TEXT")
        self._ensure_column("mission_controls", "action_usage_json", "TEXT")
        self.conn.execute(
            """
            INSERT INTO schema_version (version, updated_at)
            SELECT 1, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (SELECT 1 FROM schema_version)
            """
        )
        self.conn.commit()

    def _ensure_column(self, table_name: str, column_name: str, definition: str) -> None:
        columns = self.fetchall(f"PRAGMA table_info({table_name})")
        if any(column.get("name") == column_name for column in columns):
            return
        try:
            self.conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
        except Exception:
            pass

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        if self.conn is None:
            raise sqlite3.ProgrammingError("Cannot operate on a closed database.")
        cur = self.conn.execute(sql, tuple(params))
        self.conn.commit()
        return cur

    def fetchall(self, sql: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
        if self.conn is None:
            raise sqlite3.ProgrammingError("Cannot operate on a closed database.")
        cur = self.conn.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]

    def fetchone(self, sql: str, params: Iterable[Any] = ()) -> Optional[Dict[str, Any]]:
        if self.conn is None:
            raise sqlite3.ProgrammingError("Cannot operate on a closed database.")
        cur = self.conn.execute(sql, tuple(params))
        row = cur.fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        if getattr(self, "conn", None) is not None:
            self.conn.close()
            self.conn = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Public factory — Database(path) auto-picks the right backend
# ─────────────────────────────────────────────────────────────────────────────

class Database:
    """
    Public database handle.  Instantiate exactly as before:

        db = Database(config.db_path)
        db.init()

    If DATABASE_URL is set in the environment, connects to Supabase PostgreSQL.
    Otherwise falls back to local SQLite at db_path.
    """

    def __new__(cls, db_path: str) -> Any:  # type: ignore[override]
        database_url = os.environ.get("DATABASE_URL", "").strip()
        if database_url:
            import logging
            logging.getLogger("db").info(
                "DATABASE_URL detected — connecting to Supabase PostgreSQL"
            )
            try:
                instance = _PostgresDatabase(database_url)
                return instance
            except Exception as exc:
                import logging
                logging.getLogger("db").warning(
                    "Supabase connection failed (%s) — falling back to SQLite", exc
                )
                # Fall through to SQLite
        return _SQLiteDatabase(db_path)
