from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    from .repository import MissionRepository, TaskRepository
    from .state_machine import MissionStateMachine, StateValidationError
except ImportError:  # pragma: no cover - runtime script compatibility
    from repository import MissionRepository, TaskRepository
    from state_machine import MissionStateMachine, StateValidationError

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


@dataclass
class Scheduler:
    mission_repository: MissionRepository
    task_repository: TaskRepository
    state_updater: Optional[object] = None  # TransactionalStateUpdater

    def list_active_missions(self) -> List[Dict]:
        missions = self.mission_repository.list_missions()
        return [m for m in missions if m["status"] in {"queued", "running", "blocked"}]

    def mission_execution_state(self, mission_id: str) -> str:
        tasks = self.task_repository.list_tasks_for_mission(mission_id)
        if any(task["status"] == "running" for task in tasks):
            return "running"

        done_ids = {task["id"] for task in tasks if task["status"] in {"done", "completed"}}
        ready_pending = []
        blocked_waiting = []
        for task in tasks:
            if task["status"] not in {"pending", "blocked"}:
                continue
            deps = task.get("depends_on") or []
            if all(dep in done_ids for dep in deps):
                ready_pending.append(task)
            else:
                blocked_waiting.append(task)

        if ready_pending:
            return "ready"
        if blocked_waiting:
            return "blocked"
        return "idle"

    def highest_priority_mission(self) -> Optional[Dict]:
        missions = self.list_active_missions()
        if not missions:
            return None
        return sorted(
            missions,
            key=lambda item: (
                1 if self.mission_execution_state(item["id"]) in {"running", "ready"} else 0,
                PRIORITY_SCORE.get(item["priority"], 0),
                STATUS_SCORE.get(item["status"], 0),
                item["updated_at"],
                item["created_at"],
            ),
            reverse=True,
        )[0]

    def should_interrupt(self, current_priority: str, incoming_priority: str) -> bool:
        return PRIORITY_SCORE.get(incoming_priority, 0) > PRIORITY_SCORE.get(current_priority, 0)

    def resolve_conflict(self, current_priority: str, incoming_priority: str, incoming_source: str) -> Dict:
        if self.should_interrupt(current_priority, incoming_priority):
            return {
                "decision": "interrupt",
                "reason": "incoming_higher_priority",
            }
        if incoming_source == "manual" and current_priority in {"high", "critical"}:
            return {
                "decision": "notify_user",
                "reason": "manual_request_conflicts_with_important_work",
            }
        return {
            "decision": "queue",
            "reason": "existing_work_keeps_priority",
        }

    def pause_other_running_missions(self, active_mission_id: str) -> List[str]:
        """Pause all running missions except the active one using state machine transitions."""
        running_missions = self.mission_repository.db.fetchall(
            "SELECT id FROM missions WHERE status = 'running' AND id != ? ORDER BY created_at DESC",
            (active_mission_id,),
        )
        paused_ids = [mission["id"] for mission in running_missions]
        if not paused_ids:
            return []

        if self.state_updater:
            # Use transactional state updater to pause missions with validation
            try:
                self.state_updater.begin_transaction()
                for mission in running_missions:
                    self.state_updater.transition_mission(
                        mission["id"],
                        "queued",
                        reason="pause_for_new_priority",
                        actor="scheduler"
                    )
                self.state_updater.commit_transaction()
            except StateValidationError as e:
                # Log error but continue (some transitions may be invalid)
                # In production, should notify and continue
                self.state_updater.rollback_transaction()
                # Fallback: attempt direct pause without validation? Better to log and skip
                raise
        else:
            # Legacy direct update (without validation)
            now = self.mission_repository.db.utc_now() if hasattr(self.mission_repository.db, 'utc_now') else None
            # Simple implementación legada
            for mission_id in paused_ids:
                self.mission_repository.update_mission_status(mission_id, "queued")
        return paused_ids

    def summary(self) -> Dict:
        active = self.list_active_missions()
        top = self.highest_priority_mission()
        queued = []
        blocked = []
        for mission in active:
            item = {
                "id": mission["id"],
                "title": mission["title"],
                "priority": mission["priority"],
                "status": mission["status"],
                "execution_state": self.mission_execution_state(mission["id"]),
            }
            if mission["status"] == "queued":
                queued.append(item)
            elif mission["status"] == "blocked":
                blocked.append(item)
        return {
            "active_count": len(active),
            "highest_priority_mission": top["id"] if top else None,
            "highest_priority_mission_execution_state": self.mission_execution_state(top["id"]) if top else None,
            "queued_missions": queued,
            "blocked_missions": blocked,
        }
