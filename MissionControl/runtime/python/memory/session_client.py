"""
Session Store client - Async SQLite operations for session state, diffs, checkpoints
Uses aiosqlite for async compatibility with LangGraph
"""

import os
import json
import hashlib
from typing import Optional, Dict, Any, List
from pathlib import Path
import aiosqlite
import asyncio

class SessionClient:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv("MISSION_CONTROL_DB", "./data/sessions.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema_sync()

    def _ensure_schema_sync(self):
        """Synchronously ensure schema exists (called in __init__)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        schema_path = Path(__file__).parent.parent.parent / "src" / "session_schema.sql"
        if schema_path.exists():
            cursor.executescript(schema_path.read_text())
        conn.commit()
        conn.close()

    async def _get_conn(self) -> aiosqlite.Connection:
        return await aiosqlite.connect(self.db_path)

    async def create_session(self, mission_id: str, agent_id: str, session_token: str) -> int:
        conn = await self._get_conn()
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT OR IGNORE INTO runtime_sessions (mission_id, agent_id, session_token, state_json, last_activity)
            VALUES (?, ?, ?, '{}', CURRENT_TIMESTAMP)
        """, (mission_id, agent_id, session_token))
        lastrowid = cursor.lastrowid
        if lastrowid:
            session_id = lastrowid
        else:
            await cursor.execute("SELECT id FROM runtime_sessions WHERE session_token = ?", (session_token,))
            row = await cursor.fetchone()
            session_id = row[0]
        await conn.commit()
        await conn.close()
        return session_id

    async def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        conn = await self._get_conn()
        cursor = await conn.cursor()
        await cursor.execute("SELECT * FROM runtime_sessions WHERE session_token = ?", (session_token,))
        row = await cursor.fetchone()
        await conn.close()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None

    async def update_session_state(self, session_token: str, new_state: Dict[str, Any], diff_ops: Optional[Dict] = None) -> Dict[str, Any]:
        session = await self.get_session(session_token)
        if not session:
            raise ValueError(f"Session not found: {session_token}")

        prev_state = json.loads(session['state_json'] or '{}')
        new_state_json = json.dumps(new_state)
        prev_hash = self._state_hash(prev_state)
        new_hash = self._state_hash(new_state)

        conn = await self._get_conn()
        cursor = await conn.cursor()
        await cursor.execute("""
            UPDATE runtime_sessions
            SET state_json = ?, last_activity = CURRENT_TIMESTAMP, token_usage = token_usage + ?
            WHERE session_token = ?
        """, (new_state_json, self._estimate_token_delta(prev_state, new_state), session_token))

        if diff_ops is None:
            diff_ops = self._compute_diff(prev_state, new_state)

        if diff_ops:
            await cursor.execute("SELECT COALESCE(MAX(seq_num), 0) + 1 as next_seq FROM session_diffs WHERE session_id = ?", (session['id'],))
            seq_row = await cursor.fetchone()
            seq = seq_row[0] if seq_row else 1
            await cursor.execute("""
                INSERT INTO session_diffs (session_id, seq_num, diff_json, prev_state_hash, new_state_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (session['id'], seq, json.dumps(diff_ops), prev_hash, new_hash))

        await conn.commit()
        await conn.close()
        return {'prev_hash': prev_hash, 'new_hash': new_hash, 'diff': diff_ops}

    def _compute_diff(self, old: Dict, new: Dict) -> Dict:
        diff = {}
        for key, value in new.items():
            if key not in old:
                diff[key] = {'op': 'add', 'value': value}
            elif json.dumps(old[key], sort_keys=True) != json.dumps(new[key], sort_keys=True):
                diff[key] = {'op': 'replace', 'value': value}
        for key in old:
            if key not in new:
                diff[key] = {'op': 'remove'}
        return diff

    def _state_hash(self, state: Dict) -> str:
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()

    def _estimate_token_delta(self, old: Dict, new: Dict) -> int:
        old_len = len(json.dumps(old))
        new_len = len(json.dumps(new))
        return max(0, (new_len - old_len) // 4)

    async def get_diffs_since_checkpoint(self, session_token: str, checkpoint_created_at: Optional[str] = None) -> List[Dict]:
        session = await self.get_session(session_token)
        if not session:
            return []
        conn = await self._get_conn()
        cursor = await conn.cursor()
        if checkpoint_created_at:
            await cursor.execute("""
                SELECT seq_num, diff_json, created_at FROM session_diffs
                WHERE session_id = ? AND created_at >= ?
                ORDER BY seq_num ASC
            """, (session['id'], checkpoint_created_at))
        else:
            await cursor.execute("""
                SELECT seq_num, diff_json, created_at FROM session_diffs
                WHERE session_id = ? ORDER BY seq_num ASC
            """, (session['id'],))
        rows = await cursor.fetchall()
        await conn.close()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    async def create_checkpoint(
        self,
        session_token: str,
        supabase_snapshot_id: Optional[str] = None,
        checkpoint_type: str = 'automatic',
        reason: Optional[str] = None
    ) -> int:
        session = await self.get_session(session_token)
        if not session:
            raise ValueError(f"Session not found: {session_token}")
        conn = await self._get_conn()
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT INTO session_checkpoints (session_id, supabase_snapshot_id, checkpoint_type, reason)
            VALUES (?, ?, ?, ?)
        """, (session['id'], supabase_snapshot_id, checkpoint_type, reason))
        checkpoint_id = cursor.lastrowid
        await conn.commit()
        await conn.close()
        return checkpoint_id

    async def cleanup_old_sessions(self, max_age_days: int = 7) -> int:
        conn = await self._get_conn()
        cursor = await conn.cursor()
        await cursor.execute("""
            UPDATE runtime_sessions
            SET is_active = 0
            WHERE is_active = 1 AND datetime(last_activity) < datetime('now', ?)
        """, (f"-{max_age_days} days",))
        changed = cursor.rowcount
        await conn.commit()
        await conn.close()
        return changed

    async def purge_old_diffs(self, keep_checkpoints: int = 10) -> int:
        """Delete diffs older than the keep_checkpoints most recent per session."""
        conn = await self._get_conn()
        cursor = await conn.cursor()
        # Find diffs to delete
        await cursor.execute("""
            SELECT session_id, seq_num FROM session_diffs
            WHERE (session_id, seq_num) IN (
              SELECT session_id, seq_num FROM session_diffs sd
              WHERE seq_num < (
                SELECT seq_num FROM session_diffs sd2
                WHERE sd2.session_id = sd.session_id
                ORDER BY seq_num DESC LIMIT 1 OFFSET ?
              )
            )
        """, (keep_checkpoints,))
        rows = await cursor.fetchall()
        for session_id, seq_num in rows:
            await cursor.execute("DELETE FROM session_diffs WHERE session_id = ? AND seq_num = ?", (session_id, seq_num))
        await conn.commit()
        await conn.close()
        return len(rows)

    async def get_pending_sync_queue(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = await self._get_conn()
        cursor = await conn.cursor()
        await cursor.execute("""
            SELECT * FROM memory_sync_queue
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        await conn.close()
        if not rows:
            return []
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    async def mark_sync_complete(self, queue_id: int):
        conn = await self._get_conn()
        cursor = await conn.cursor()
        await cursor.execute("DELETE FROM memory_sync_queue WHERE id = ?", (queue_id,))
        await conn.commit()
        await conn.close()

    async def queue_sync_operation(self, direction: str, table_name: str, record_id: str, payload: Dict):
        conn = await self._get_conn()
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT INTO memory_sync_queue (direction, table_name, record_id, payload_json)
            VALUES (?, ?, ?, ?)
        """, (direction, table_name, record_id, json.dumps(payload)))
        await conn.commit()
        await conn.close()