from dataclasses import dataclass
from typing import Dict, Optional

from repository import MissionRepository, TaskRepository


@dataclass
class MissionLifecycleService:
    mission_repository: MissionRepository
    task_repository: TaskRepository

    def activate(self, mission_id: str) -> None:
        mission = self.mission_repository.get_mission(mission_id)
        if not mission:
            return
        self.mission_repository.update_mission_status(mission_id, "running")
        self.mission_repository.add_event(mission_id, "mission_activated", "system", "Mission activated", {"mission_id": mission_id})

    def mark_mission_done_if_ready(self, mission_id: str) -> bool:
        tasks = self.task_repository.list_tasks_for_mission(mission_id)
        if not tasks:
            return False
        if any(task["status"] in {"pending", "running", "blocked"} for task in tasks):
            return False
        self.mission_repository.update_mission_status(mission_id, "completed")
        self.mission_repository.add_event(mission_id, "mission_completed", "system", "Mission completed", {"mission_id": mission_id})
        return True

    def mission_progress(self, mission_id: str) -> Dict:
        tasks = self.task_repository.list_tasks_for_mission(mission_id)
        total = len(tasks)
        done = sum(1 for task in tasks if task["status"] == "done")
        blocked = sum(1 for task in tasks if task["status"] == "blocked")
        running = sum(1 for task in tasks if task["status"] == "running")
        return {
            "total": total,
            "done": done,
            "blocked": blocked,
            "running": running,
            "percent": int((done / total) * 100) if total else 0,
        }
