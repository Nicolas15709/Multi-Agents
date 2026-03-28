from dataclasses import dataclass
from repository import MissionRepository, TaskRepository


@dataclass
class ProgressSummaryService:
    mission_repository: MissionRepository
    task_repository: TaskRepository

    def latest(self):
        missions = self.mission_repository.list_missions()
        if not missions:
            return {"mission": None}
        mission = missions[0]
        tasks = self.task_repository.list_tasks_for_mission(mission["id"])
        total = len(tasks)
        done = sum(1 for task in tasks if task["status"] == "done")
        running = sum(1 for task in tasks if task["status"] == "running")
        blocked = sum(1 for task in tasks if task["status"] == "blocked")
        percent = int((done / total) * 100) if total else 0
        return {
            "mission": {
                "id": mission["id"],
                "title": mission["title"],
                "status": mission["status"],
                "priority": mission["priority"],
            },
            "progress": {
                "total": total,
                "done": done,
                "running": running,
                "blocked": blocked,
                "percent": percent,
            },
        }
