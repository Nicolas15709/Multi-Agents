from dataclasses import dataclass
from typing import Dict, List, Optional

from repository import MissionRepository, TaskRepository

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

    def summary(self) -> Dict:
        active = self.list_active_missions()
        top = self.highest_priority_mission()
        return {
            "active_count": len(active),
            "highest_priority_mission": top["id"] if top else None,
            "highest_priority_mission_execution_state": self.mission_execution_state(top["id"]) if top else None,
        }
