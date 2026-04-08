import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from .storage import ensure_parent
except ImportError:  # pragma: no cover - runtime script compatibility
    from storage import ensure_parent

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"


class Database:
    def __init__(self, db_path: str):
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
        self.conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

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

    def __del__(self) -> None:  # pragma: no cover - defensive cleanup for tests/process shutdown
        try:
            self.close()
        except Exception:
            pass
