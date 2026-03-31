import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .db import Database
from .models import AgentRecord, Mission, NotificationRecord, PolicyRecord, Task
from .utils import to_json, utc_now


class MissionRepository:
    ACTIVE_STATUSES = {"queued", "running", "blocked"}
    PRIORITY_SCORE = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }
    STATUS_SCORE = {
        "running": 3,
        "blocked": 2,
        "queued": 1,
    }

    def __init__(self, db: Database):
        self.db = db

    def create_mission(self, mission: Mission) -> None:
        now = utc_now()
        self.db.execute(
            """
            INSERT INTO missions (id, title, goal, mode, priority, status, source, schedule, allow_24x7, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mission.id,
                mission.title,
                mission.goal,
                mission.mode,
                mission.priority,
                mission.status,
                mission.source,
                mission.schedule,
                1 if mission.allow_24x7 else 0,
                now,
                now,
            ),
        )

    def list_missions(self) -> List[Dict]:
        return self.db.fetchall("SELECT * FROM missions ORDER BY created_at DESC")

    def list_active_missions(self) -> List[Dict]:
        return [mission for mission in self.list_missions() if mission["status"] in self.ACTIVE_STATUSES]

    def get_focus_mission(self) -> Optional[Dict]:
        active = self.list_active_missions()
        if active:
            return sorted(
                active,
                key=lambda item: (
                    self.STATUS_SCORE.get(item["status"], 0),
                    self.PRIORITY_SCORE.get(item["priority"], 0),
                    item["updated_at"],
                    item["created_at"],
                ),
                reverse=True,
            )[0]
        missions = self.list_missions()
        return missions[0] if missions else None

    def pause_other_running_missions(self, active_mission_id: str) -> List[str]:
        running_missions = self.db.fetchall(
            "SELECT id FROM missions WHERE status = 'running' AND id != ? ORDER BY created_at DESC",
            (active_mission_id,),
        )
        paused_ids = [mission["id"] for mission in running_missions]
        if not paused_ids:
            return []

        now = utc_now()
        self.db.execute(
            "UPDATE missions SET status = 'queued', updated_at = ? WHERE status = 'running' AND id != ?",
            (now, active_mission_id),
        )
        return paused_ids

    def get_mission(self, mission_id: str) -> Optional[Dict]:
        return self.db.fetchone("SELECT * FROM missions WHERE id = ?", (mission_id,))

    def latest_active_mission(self) -> Optional[Dict]:
        return self.db.fetchone(
            """
            SELECT * FROM missions
            WHERE status IN ('queued', 'running', 'blocked')
            ORDER BY CASE status
                WHEN 'running' THEN 3
                WHEN 'blocked' THEN 2
                WHEN 'queued' THEN 1
                ELSE 0
            END DESC, created_at DESC
            LIMIT 1
            """
        )

    def update_mission_status(self, mission_id: str, status: str) -> None:
        self.db.execute(
            "UPDATE missions SET status = ?, updated_at = ? WHERE id = ?",
            (status, utc_now(), mission_id),
        )

    def add_event(self, mission_id: str, event_type: str, actor: str, summary: str, payload: Dict = None) -> None:
        self.db.execute(
            "INSERT INTO mission_events (mission_id, event_type, actor, summary, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (mission_id, event_type, actor, summary, to_json(payload or {}), utc_now()),
        )

    def recent_events(self, mission_id: Optional[str] = None, limit: int = 20) -> List[Dict]:
        if mission_id:
            rows = self.db.fetchall(
                "SELECT * FROM mission_events WHERE mission_id = ? ORDER BY id DESC LIMIT ?",
                (mission_id, limit),
            )
        else:
            rows = self.db.fetchall("SELECT * FROM mission_events ORDER BY id DESC LIMIT ?", (limit,))
        return [self._decode_payload(row) for row in rows]

    def _decode_payload(self, row: Dict) -> Dict:
        payload = row.get("payload_json")
        try:
            row["payload"] = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            row["payload"] = {}
        return row


class TaskRepository:
    def __init__(self, db: Database):
        self.db = db

    def create_task(self, task: Task) -> None:
        now = utc_now()
        self.db.execute(
            """
            INSERT INTO tasks (id, mission_id, agent_id, title, status, priority, depends_on, details_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.mission_id,
                task.agent_id,
                task.title,
                task.status,
                task.priority,
                json.dumps(task.depends_on),
                to_json(task.details),
                now,
                now,
            ),
        )

    def list_tasks_for_mission(self, mission_id: str) -> List[Dict]:
        rows = self.db.fetchall("SELECT * FROM tasks WHERE mission_id = ? ORDER BY created_at ASC", (mission_id,))
        return [self._decode_fields(row) for row in rows]

    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a single task by ID."""
        row = self.db.fetchone("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return self._decode_fields(row) if row else None

    def update_task_status(self, task_id: str, status: str) -> None:
        self.db.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
            (status, utc_now(), task_id),
        )

    def _decode_fields(self, row: Dict) -> Dict:
        try:
            row["depends_on"] = json.loads(row.get("depends_on") or "[]")
        except json.JSONDecodeError:
            row["depends_on"] = []
        try:
            row["details"] = json.loads(row.get("details_json") or "{}")
        except json.JSONDecodeError:
            row["details"] = {}
        return row


class AgentRepository:
    def __init__(self, db: Database):
        self.db = db

    def upsert_agent(self, agent: AgentRecord) -> None:
        self.db.execute(
            """
            INSERT INTO agent_status (agent_id, display_name, role, state, active_mission_id, current_task_id, personality, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
              display_name=excluded.display_name,
              role=excluded.role,
              state=excluded.state,
              active_mission_id=excluded.active_mission_id,
              current_task_id=excluded.current_task_id,
              personality=excluded.personality,
              updated_at=excluded.updated_at
            """,
            (
                agent.agent_id,
                agent.display_name,
                agent.role,
                agent.state,
                agent.active_mission_id,
                agent.current_task_id,
                agent.personality,
                utc_now(),
            ),
        )

    def list_agents(self) -> List[Dict]:
        return self.db.fetchall("SELECT * FROM agent_status ORDER BY agent_id ASC")

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get a single agent by ID."""
        return self.db.fetchone("SELECT * FROM agent_status WHERE agent_id = ?", (agent_id,))


class PolicyRepository:
    def __init__(self, db: Database):
        self.db = db

    def upsert_policy(self, policy: PolicyRecord) -> None:
        self.db.execute(
            """
            INSERT INTO policies (id, integration, account_resource, action, mode, conditions_json, enabled, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              integration=excluded.integration,
              account_resource=excluded.account_resource,
              action=excluded.action,
              mode=excluded.mode,
              conditions_json=excluded.conditions_json,
              enabled=excluded.enabled,
              updated_at=excluded.updated_at
            """,
            (
                policy.id,
                policy.integration,
                policy.account_resource,
                policy.action,
                policy.mode,
                to_json(policy.conditions),
                1 if policy.enabled else 0,
                utc_now(),
            ),
        )

    def list_policies(self) -> List[Dict]:
        return self.db.fetchall("SELECT * FROM policies ORDER BY integration, account_resource, action")


class NotificationRepository:
    def __init__(self, db: Database):
        self.db = db

    def create_notification(self, notification: NotificationRecord) -> None:
        self.db.execute(
            "INSERT INTO notifications (channel, kind, status, summary, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                notification.channel,
                notification.kind,
                notification.status,
                notification.summary,
                to_json(notification.payload),
                utc_now(),
            ),
        )

    def recent_notifications(self, limit: int = 20) -> List[Dict]:
        rows = self.db.fetchall("SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,))
        return [self._decode_payload(row) for row in rows]

    def _decode_payload(self, row: Dict) -> Dict:
        payload = row.get("payload_json")
        try:
            row["payload"] = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            row["payload"] = {}
        return row
