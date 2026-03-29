from dataclasses import dataclass
from typing import Dict, Optional

from repository import MissionRepository, TaskRepository


@dataclass
class MissionLifecycleService:
    mission_repository: MissionRepository
    task_repository: TaskRepository

    def activate(self, mission_id: str) -> bool:
        mission = self.mission_repository.get_mission(mission_id)
        if not mission:
            return False

        paused_ids = self.mission_repository.pause_other_running_missions(mission_id)
        for paused_id in paused_ids:
            self.mission_repository.add_event(
                paused_id,
                "mission_paused",
                "system",
                "Mission paused while another mission takes focus",
                {"paused_for_mission_id": mission_id},
            )

        if mission.get("status") != "running":
            self.mission_repository.update_mission_status(mission_id, "running")
            self.mission_repository.add_event(mission_id, "mission_activated", "system", "Mission activated", {"mission_id": mission_id})
            return True

        if paused_ids:
            self.mission_repository.add_event(
                mission_id,
                "mission_reaffirmed",
                "system",
                "Mission kept runtime focus after resolving competing running missions",
                {"mission_id": mission_id, "paused_mission_ids": paused_ids},
            )
            return True

        return False

    def mark_mission_done_if_ready(self, mission_id: str) -> bool:
        mission = self.mission_repository.get_mission(mission_id)
        if not mission or mission.get("status") == "completed":
            return False

        tasks = self.task_repository.list_tasks_for_mission(mission_id)
        if not tasks:
            return False
        if any(task["status"] in {"pending", "running", "blocked"} for task in tasks):
            return False
        failed_tasks = [task for task in tasks if task["status"] == "failed"]
        if failed_tasks:
            self.mission_repository.update_mission_status(mission_id, "needs_human")
            self.mission_repository.add_event(
                mission_id,
                "mission_needs_human",
                "system",
                "Mission requires human attention before it can complete",
                {
                    "mission_id": mission_id,
                    "failed_task_ids": [task["id"] for task in failed_tasks],
                },
            )
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
        failed = sum(1 for task in tasks if task["status"] == "failed")
        return {
            "total": total,
            "done": done,
            "blocked": blocked,
            "running": running,
            "failed": failed,
            "percent": int((done / total) * 100) if total else 0,
        }
