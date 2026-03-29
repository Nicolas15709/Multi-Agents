from dataclasses import dataclass
from repository import MissionRepository, TaskRepository


@dataclass
class MissionSummaryService:
    mission_repository: MissionRepository
    task_repository: TaskRepository

    def build(self, mission_id: str):
        mission = self.mission_repository.get_mission(mission_id)
        if not mission:
            return None
        tasks = self.task_repository.list_tasks_for_mission(mission_id)
        return {
            "mission": {
                "id": mission["id"],
                "title": mission["title"],
                "goal": mission["goal"],
                "mode": mission["mode"],
                "priority": mission["priority"],
                "status": mission["status"],
                "source": mission["source"],
            },
            "tasks": [
                {
                    "id": task["id"],
                    "agent_id": task["agent_id"],
                    "title": task["title"],
                    "status": task["status"],
                    "priority": task["priority"],
                }
                for task in tasks
            ],
            "counts": {
                "total": len(tasks),
                "done": sum(1 for task in tasks if task["status"] == "done"),
                "running": sum(1 for task in tasks if task["status"] == "running"),
                "pending": sum(1 for task in tasks if task["status"] == "pending"),
                "blocked": sum(1 for task in tasks if task["status"] == "blocked"),
                "failed": sum(1 for task in tasks if task["status"] == "failed"),
            },
        }
