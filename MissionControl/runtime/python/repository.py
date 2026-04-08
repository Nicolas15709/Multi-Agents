import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from .db import Database
    from .models import (
        ActionApprovalRecord,
        AgentHireRequestRecord,
        AgentMessageRecord,
        AgentRecord,
        IntakeRequestRecord,
        Mission,
        MissionControlRecord,
        MissionMemoryRecord,
        NotificationRecord,
        PolicyRecord,
        Task,
    )
    from .utils import to_json, utc_now
except ImportError:  # pragma: no cover - runtime script compatibility
    from db import Database
    from models import (
        ActionApprovalRecord,
        AgentHireRequestRecord,
        AgentMessageRecord,
        AgentRecord,
        IntakeRequestRecord,
        Mission,
        MissionControlRecord,
        MissionMemoryRecord,
        NotificationRecord,
        PolicyRecord,
        Task,
    )
    from utils import to_json, utc_now


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
        "queued": 2,
        "blocked": 1,
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

    def update_task_details(self, task_id: str, details: Dict) -> None:
        self.db.execute(
            "UPDATE tasks SET details_json = ?, updated_at = ? WHERE id = ?",
            (to_json(details), utc_now(), task_id),
        )

    def update_task_dependencies(self, task_id: str, depends_on: List[str]) -> None:
        self.db.execute(
            "UPDATE tasks SET depends_on = ?, updated_at = ? WHERE id = ?",
            (json.dumps(depends_on), utc_now(), task_id),
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

    def _hydrate_profile(self, row: Optional[Dict]) -> Optional[Dict]:
        if not row:
            return row
        try:
            row["capabilities"] = json.loads(row.get("capabilities_json") or "[]")
        except json.JSONDecodeError:
            row["capabilities"] = []
        try:
            row["metadata"] = json.loads(row.get("metadata_json") or "{}")
        except json.JSONDecodeError:
            row["metadata"] = {}
        return row

    def upsert_agent(self, agent: AgentRecord) -> None:
        now = utc_now()
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
                now,
            ),
        )
        self.db.execute(
            """
            INSERT INTO agent_profiles (
              agent_id, reports_to, capabilities_json, budget_monthly_cents, origin,
              mission_scope_id, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
              reports_to=excluded.reports_to,
              capabilities_json=excluded.capabilities_json,
              budget_monthly_cents=excluded.budget_monthly_cents,
              origin=excluded.origin,
              mission_scope_id=excluded.mission_scope_id,
              metadata_json=excluded.metadata_json,
              updated_at=excluded.updated_at
            """,
            (
                agent.agent_id,
                agent.reports_to,
                to_json(agent.capabilities),
                int(agent.budget_monthly_cents or 0),
                agent.origin or "core",
                agent.mission_scope_id,
                to_json(agent.metadata or {}),
                now,
                now,
            ),
        )

    def list_agents(self) -> List[Dict]:
        rows = self.db.fetchall(
            """
            SELECT s.*, p.reports_to, p.capabilities_json, p.budget_monthly_cents, p.origin,
                   p.mission_scope_id, p.metadata_json
            FROM agent_status s
            LEFT JOIN agent_profiles p ON p.agent_id = s.agent_id
            ORDER BY s.agent_id ASC
            """
        )
        return [self._hydrate_profile(row) for row in rows]

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get a single agent by ID."""
        row = self.db.fetchone(
            """
            SELECT s.*, p.reports_to, p.capabilities_json, p.budget_monthly_cents, p.origin,
                   p.mission_scope_id, p.metadata_json
            FROM agent_status s
            LEFT JOIN agent_profiles p ON p.agent_id = s.agent_id
            WHERE s.agent_id = ?
            """,
            (agent_id,),
        )
        return self._hydrate_profile(row)

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent by ID. Returns True if a row was deleted."""
        self.db.execute("DELETE FROM agent_profiles WHERE agent_id = ?", (agent_id,))
        self.db.execute("DELETE FROM agent_status WHERE agent_id = ?", (agent_id,))
        return True


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


class IntakeRequestRepository:
    ACTIVE_STATUSES = {"pending", "dispatched"}

    def __init__(self, db: Database):
        self.db = db

    def create_request(self, request: IntakeRequestRecord) -> None:
        now = utc_now()
        self.db.execute(
            """
            INSERT INTO intake_requests (
              id, title, description, status, priority, requested_by, channel,
              source, mode, fingerprint, mission_id, details_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.id,
                request.title,
                request.description,
                request.status,
                request.priority,
                request.requested_by,
                request.channel,
                request.source,
                request.mode,
                request.fingerprint,
                request.mission_id,
                to_json(request.details),
                now,
                now,
            ),
        )

    def list_requests(self, limit: int = 50) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM intake_requests ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [self._decode_fields(row) for row in rows]

    def list_requests_by_status(self, statuses: List[str], limit: int = 50) -> List[Dict]:
        if not statuses:
            return []
        placeholders = ",".join(["?"] * len(statuses))
        rows = self.db.fetchall(
            f"SELECT * FROM intake_requests WHERE status IN ({placeholders}) ORDER BY created_at ASC LIMIT ?",
            (*statuses, limit),
        )
        return [self._decode_fields(row) for row in rows]

    def get_request(self, request_id: str) -> Optional[Dict]:
        row = self.db.fetchone("SELECT * FROM intake_requests WHERE id = ?", (request_id,))
        return self._decode_fields(row) if row else None

    def find_active_duplicate(self, fingerprint: str) -> Optional[Dict]:
        if not fingerprint:
            return None
        placeholders = ",".join(["?"] * len(self.ACTIVE_STATUSES))
        row = self.db.fetchone(
            f"""
            SELECT * FROM intake_requests
            WHERE fingerprint = ? AND status IN ({placeholders})
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (fingerprint, *self.ACTIVE_STATUSES),
        )
        return self._decode_fields(row) if row else None

    def update_request_status(self, request_id: str, status: str, mission_id: Optional[str] = None, details: Optional[Dict] = None) -> None:
        existing = self.get_request(request_id) or {}
        merged_details = dict(existing.get("details") or {})
        if details:
            merged_details.update(details)
        resolved_mission_id = mission_id if mission_id is not None else existing.get("mission_id")
        self.db.execute(
            """
            UPDATE intake_requests
            SET status = ?, mission_id = ?, details_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, resolved_mission_id, to_json(merged_details), utc_now(), request_id),
        )

    def _decode_fields(self, row: Dict) -> Dict:
        if row is None:
            return row
        try:
            row["details"] = json.loads(row.get("details_json") or "{}")
        except json.JSONDecodeError:
            row["details"] = {}
        return row


class AgentHireRequestRepository:
    def __init__(self, db: Database):
        self.db = db

    def create_request(self, request: AgentHireRequestRecord) -> None:
        now = utc_now()
        self.db.execute(
            """
            INSERT INTO agent_hire_requests (
              id, mission_id, requested_by_agent_id, display_name, role, personality,
              capabilities_json, budget_monthly_cents, reports_to, notes, status,
              hired_agent_id, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.id,
                request.mission_id,
                request.requested_by_agent_id,
                request.display_name,
                request.role,
                request.personality,
                to_json(request.capabilities),
                int(request.budget_monthly_cents or 0),
                request.reports_to,
                request.notes,
                request.status,
                request.hired_agent_id,
                to_json(request.metadata or {}),
                now,
                now,
            ),
        )

    def list_requests_for_mission(self, mission_id: str) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM agent_hire_requests WHERE mission_id = ? ORDER BY created_at DESC",
            (mission_id,),
        )
        return [self._decode_fields(row) for row in rows]

    def get_request(self, request_id: str) -> Optional[Dict]:
        row = self.db.fetchone("SELECT * FROM agent_hire_requests WHERE id = ?", (request_id,))
        return self._decode_fields(row) if row else None

    def find_active_request_for_mission(self, mission_id: str, display_name: str, role: str) -> Optional[Dict]:
        row = self.db.fetchone(
            """
            SELECT * FROM agent_hire_requests
            WHERE mission_id = ? AND lower(display_name) = lower(?) AND lower(role) = lower(?)
              AND status IN ('pending', 'approved', 'hired')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (mission_id, display_name, role),
        )
        return self._decode_fields(row) if row else None

    def update_request(
        self,
        request_id: str,
        *,
        status: str,
        hired_agent_id: Optional[str] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        existing = self.get_request(request_id) or {}
        self.db.execute(
            """
            UPDATE agent_hire_requests
            SET status = ?, hired_agent_id = ?, notes = ?, metadata_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                hired_agent_id if hired_agent_id is not None else existing.get("hired_agent_id"),
                notes if notes is not None else existing.get("notes"),
                to_json(metadata if metadata is not None else existing.get("metadata") or {}),
                utc_now(),
                request_id,
            ),
        )

    def _decode_fields(self, row: Dict) -> Dict:
        if row is None:
            return row
        try:
            row["capabilities"] = json.loads(row.get("capabilities_json") or "[]")
        except json.JSONDecodeError:
            row["capabilities"] = []
        try:
            row["metadata"] = json.loads(row.get("metadata_json") or "{}")
        except json.JSONDecodeError:
            row["metadata"] = {}
        return row


class MissionControlRepository:
    def __init__(self, db: Database):
        self.db = db

    def _hydrate_control(self, row: Optional[Dict]) -> Optional[Dict]:
        if not row:
            return row
        try:
            row["action_budgets"] = json.loads(row.get("action_budgets_json") or "{}")
        except json.JSONDecodeError:
            row["action_budgets"] = {}
        try:
            row["action_usage"] = json.loads(row.get("action_usage_json") or "{}")
        except json.JSONDecodeError:
            row["action_usage"] = {}
        return row

    def create_control(self, control: MissionControlRecord) -> None:
        now = utc_now()
        self.db.execute(
            """
            INSERT INTO mission_controls (
              mission_id, max_autonomous_steps, autonomous_steps_used,
              max_estimated_tokens, estimated_tokens_used, max_runtime_ticks,
              runtime_ticks_used, max_dynamic_hires, dynamic_hires_used,
              action_budgets_json, action_usage_json,
              status, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mission_id) DO UPDATE SET
              max_autonomous_steps=excluded.max_autonomous_steps,
              max_estimated_tokens=excluded.max_estimated_tokens,
              max_runtime_ticks=excluded.max_runtime_ticks,
              max_dynamic_hires=excluded.max_dynamic_hires,
              action_budgets_json=excluded.action_budgets_json,
              action_usage_json=excluded.action_usage_json,
              status=excluded.status,
              notes=excluded.notes,
              updated_at=excluded.updated_at
            """,
            (
                control.mission_id,
                int(control.max_autonomous_steps or 0),
                int(control.autonomous_steps_used or 0),
                int(control.max_estimated_tokens or 0),
                int(control.estimated_tokens_used or 0),
                int(control.max_runtime_ticks or 0),
                int(control.runtime_ticks_used or 0),
                int(control.max_dynamic_hires or 0),
                int(control.dynamic_hires_used or 0),
                to_json(control.action_budgets or {}),
                to_json(control.action_usage or {}),
                control.status,
                control.notes,
                now,
                now,
            ),
        )

    def get_control(self, mission_id: str) -> Optional[Dict]:
        return self._hydrate_control(self.db.fetchone("SELECT * FROM mission_controls WHERE mission_id = ?", (mission_id,)))

    def list_controls_for_missions(self, mission_ids: List[str]) -> Dict[str, Dict]:
        if not mission_ids:
            return {}
        placeholders = ",".join(["?"] * len(mission_ids))
        rows = self.db.fetchall(
            f"SELECT * FROM mission_controls WHERE mission_id IN ({placeholders})",
            tuple(mission_ids),
        )
        return {row["mission_id"]: self._hydrate_control(row) for row in rows}

    def ensure_control(self, mission_id: str, *, defaults: Dict) -> Dict:
        existing = self.get_control(mission_id)
        if existing:
            return existing
        control = MissionControlRecord(
            mission_id=mission_id,
            max_autonomous_steps=int(defaults.get("max_autonomous_steps", 18) or 18),
            max_estimated_tokens=int(defaults.get("max_estimated_tokens", 16000) or 16000),
            max_runtime_ticks=int(defaults.get("max_runtime_ticks", 64) or 64),
            max_dynamic_hires=int(defaults.get("max_dynamic_hires", 3) or 3),
            action_budgets=dict(defaults.get("action_budgets") or {}),
            action_usage=dict(defaults.get("action_usage") or {}),
            status=str(defaults.get("status", "active") or "active"),
            notes=defaults.get("notes"),
        )
        self.create_control(control)
        return self.get_control(mission_id)

    def increment_usage(
        self,
        mission_id: str,
        *,
        autonomous_steps_used: int = 0,
        estimated_tokens_used: int = 0,
        runtime_ticks_used: int = 0,
        dynamic_hires_used: int = 0,
    ) -> Dict:
        existing = self.get_control(mission_id)
        if not existing:
            raise ValueError("mission control not found")
        self.db.execute(
            """
            UPDATE mission_controls
            SET autonomous_steps_used = autonomous_steps_used + ?,
                estimated_tokens_used = estimated_tokens_used + ?,
                runtime_ticks_used = runtime_ticks_used + ?,
                dynamic_hires_used = dynamic_hires_used + ?,
                updated_at = ?
            WHERE mission_id = ?
            """,
            (
                int(autonomous_steps_used or 0),
                int(estimated_tokens_used or 0),
                int(runtime_ticks_used or 0),
                int(dynamic_hires_used or 0),
                utc_now(),
                mission_id,
            ),
        )
        return self.get_control(mission_id)

    def update_status(self, mission_id: str, *, status: str, notes: Optional[str] = None) -> Dict:
        existing = self.get_control(mission_id)
        if not existing:
            raise ValueError("mission control not found")
        self.db.execute(
            """
            UPDATE mission_controls
            SET status = ?, notes = ?, updated_at = ?
            WHERE mission_id = ?
            """,
            (
                status,
                notes if notes is not None else existing.get("notes"),
                utc_now(),
                mission_id,
            ),
        )
        return self.get_control(mission_id)

    def record_action_usage(self, mission_id: str, action_kind: str, amount: int = 1) -> Dict:
        existing = self.get_control(mission_id)
        if not existing:
            raise ValueError("mission control not found")
        usage = dict(existing.get("action_usage") or {})
        usage[action_kind] = int(usage.get(action_kind, 0) or 0) + max(0, int(amount or 0))
        self.db.execute(
            """
            UPDATE mission_controls
            SET action_usage_json = ?, updated_at = ?
            WHERE mission_id = ?
            """,
            (
                to_json(usage),
                utc_now(),
                mission_id,
            ),
        )
        return self.get_control(mission_id)

    def action_budget_status(self, mission_id: str, action_kind: str) -> Dict:
        control = self.get_control(mission_id)
        if not control:
            raise ValueError("mission control not found")
        budgets = dict(control.get("action_budgets") or {})
        usage = dict(control.get("action_usage") or {})
        limit = int(budgets.get(action_kind, 0) or 0)
        used = int(usage.get(action_kind, 0) or 0)
        return {
            "mission_id": mission_id,
            "action_kind": action_kind,
            "limit": limit,
            "used": used,
            "remaining": max(0, limit - used) if limit > 0 else None,
            "exhausted": limit > 0 and used >= limit,
        }


class MissionMemoryRepository:
    def __init__(self, db: Database):
        self.db = db

    def create_entry(self, entry: MissionMemoryRecord) -> Dict:
        new_id = self.db.execute_returning(
            """
            INSERT INTO mission_memory_entries (
              mission_id, source_task_id, author_agent_id, scope, memory_key,
              summary, content_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.mission_id,
                entry.source_task_id,
                entry.author_agent_id,
                entry.scope,
                entry.memory_key,
                entry.summary,
                to_json(entry.content),
                utc_now(),
            ),
        )
        return self.get_entry(int(new_id))

    def get_entry(self, entry_id: int) -> Optional[Dict]:
        row = self.db.fetchone("SELECT * FROM mission_memory_entries WHERE id = ?", (entry_id,))
        return self._decode_fields(row) if row else None

    def list_recent(self, mission_id: str, limit: int = 20) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM mission_memory_entries WHERE mission_id = ? ORDER BY id DESC LIMIT ?",
            (mission_id, limit),
        )
        return [self._decode_fields(row) for row in rows]

    def _decode_fields(self, row: Dict) -> Dict:
        if row is None:
            return row
        try:
            row["content"] = json.loads(row.get("content_json") or "{}")
        except json.JSONDecodeError:
            row["content"] = {}
        return row


class AgentMessageRepository:
    def __init__(self, db: Database):
        self.db = db

    def create_message(self, message: AgentMessageRecord) -> Dict:
        new_id = self.db.execute_returning(
            """
            INSERT INTO agent_messages (
              mission_id, from_agent_id, to_agent_id, source_task_id, target_task_id,
              kind, status, summary, payload_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.mission_id,
                message.from_agent_id,
                message.to_agent_id,
                message.source_task_id,
                message.target_task_id,
                message.kind,
                message.status,
                message.summary,
                to_json(message.payload),
                utc_now(),
                utc_now(),
            ),
        )
        return self.get_message(int(new_id))

    def get_message(self, message_id: int) -> Optional[Dict]:
        row = self.db.fetchone("SELECT * FROM agent_messages WHERE id = ?", (message_id,))
        return self._decode_fields(row) if row else None

    def list_messages_for_mission(self, mission_id: str, limit: int = 40) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM agent_messages WHERE mission_id = ? ORDER BY id DESC LIMIT ?",
            (mission_id, limit),
        )
        return [self._decode_fields(row) for row in rows]

    def list_pending_for_agent(self, mission_id: str, agent_id: str, *, limit: int = 20) -> List[Dict]:
        rows = self.db.fetchall(
            """
            SELECT * FROM agent_messages
            WHERE mission_id = ? AND to_agent_id = ? AND status = 'queued'
            ORDER BY id ASC LIMIT ?
            """,
            (mission_id, agent_id, limit),
        )
        return [self._decode_fields(row) for row in rows]

    def consume_for_task(self, mission_id: str, agent_id: str, task_id: str) -> List[Dict]:
        rows = self.list_pending_for_agent(mission_id, agent_id, limit=20)
        consumed_ids = [row["id"] for row in rows if not row.get("target_task_id") or row.get("target_task_id") == task_id]
        if consumed_ids:
            placeholders = ",".join(["?"] * len(consumed_ids))
            self.db.execute(
                f"UPDATE agent_messages SET status = 'consumed', updated_at = ? WHERE id IN ({placeholders})",
                (utc_now(), *consumed_ids),
            )
        return [row for row in rows if row["id"] in consumed_ids]

    def _decode_fields(self, row: Dict) -> Dict:
        if row is None:
            return row
        try:
            row["payload"] = json.loads(row.get("payload_json") or "{}")
        except json.JSONDecodeError:
            row["payload"] = {}
        return row


class ActionApprovalRepository:
    def __init__(self, db: Database):
        self.db = db

    def create_request(self, approval: ActionApprovalRecord) -> Dict:
        now = utc_now()
        self.db.execute(
            """
            INSERT INTO action_approvals (
              id, mission_id, task_id, requested_by_agent_id, action_kind, policy_mode,
              status, reason, approved_by, decision_notes, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval.id,
                approval.mission_id,
                approval.task_id,
                approval.requested_by_agent_id,
                approval.action_kind,
                approval.policy_mode,
                approval.status,
                approval.reason,
                approval.approved_by,
                approval.decision_notes,
                to_json(approval.metadata),
                now,
                now,
            ),
        )
        return self.get_request(approval.id)

    def get_request(self, approval_id: str) -> Optional[Dict]:
        row = self.db.fetchone("SELECT * FROM action_approvals WHERE id = ?", (approval_id,))
        return self._decode_fields(row) if row else None

    def find_for_task(self, task_id: str, action_kind: str) -> Optional[Dict]:
        row = self.db.fetchone(
            """
            SELECT * FROM action_approvals
            WHERE task_id = ? AND action_kind = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (task_id, action_kind),
        )
        return self._decode_fields(row) if row else None

    def list_for_mission(self, mission_id: str, limit: int = 50) -> List[Dict]:
        rows = self.db.fetchall(
            "SELECT * FROM action_approvals WHERE mission_id = ? ORDER BY created_at DESC LIMIT ?",
            (mission_id, limit),
        )
        return [self._decode_fields(row) for row in rows]

    def update_request(self, approval_id: str, *, status: str, approved_by: Optional[str] = None, decision_notes: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict:
        existing = self.get_request(approval_id)
        if not existing:
            raise ValueError("approval request not found")
        self.db.execute(
            """
            UPDATE action_approvals
            SET status = ?, approved_by = ?, decision_notes = ?, metadata_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                approved_by if approved_by is not None else existing.get("approved_by"),
                decision_notes if decision_notes is not None else existing.get("decision_notes"),
                to_json(metadata if metadata is not None else existing.get("metadata") or {}),
                utc_now(),
                approval_id,
            ),
        )
        return self.get_request(approval_id)

    def _decode_fields(self, row: Dict) -> Dict:
        if row is None:
            return row
        try:
            row["metadata"] = json.loads(row.get("metadata_json") or "{}")
        except json.JSONDecodeError:
            row["metadata"] = {}
        return row
