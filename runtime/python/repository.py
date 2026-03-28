import json
from pathlib import Path
from typing import Dict, List, Optional

from db import Database
from models import AgentRecord, Mission, NotificationRecord, PolicyRecord, Task
from utils import to_json, utc_now


class MissionRepository:
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

    def get_mission(self, mission_id: str) -> Optional[Dict]:
        return self.db.fetchone("SELECT * FROM missions WHERE id = ?", (mission_id,))

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
            return self.db.fetchall(
                "SELECT * FROM mission_events WHERE mission_id = ? ORDER BY id DESC LIMIT ?",
                (mission_id, limit),
            )
        return self.db.fetchall("SELECT * FROM mission_events ORDER BY id DESC LIMIT ?", (limit,))


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
        return self.db.fetchall("SELECT * FROM tasks WHERE mission_id = ? ORDER BY created_at ASC", (mission_id,))

    def update_task_status(self, task_id: str, status: str) -> None:
        self.db.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
            (status, utc_now(), task_id),
        )


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
        return self.db.fetchall("SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,))
