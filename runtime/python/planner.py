from dataclasses import dataclass
from typing import Dict, List

from models import Mission, Task
from repository import MissionRepository, TaskRepository
from utils import new_id


@dataclass
class Planner:
    config: object
    mission_repository: MissionRepository
    task_repository: TaskRepository

    def create_mission(self, title: str, goal: str, mode: str, priority: str = "medium", source: str = "manual", allow_24x7: bool = False) -> Mission:
        mission = Mission(
            id=new_id("mission"),
            title=title,
            goal=goal,
            mode=mode,
            priority=priority,
            source=source,
            allow_24x7=allow_24x7,
        )
        self.mission_repository.create_mission(mission)
        self.mission_repository.add_event(mission.id, "mission_created", "system", f"Mission created: {title}", {
            "mode": mode,
            "priority": priority,
            "source": source,
        })
        return mission

    def seed_base_workflow(self, mission: Mission) -> List[Task]:
        workflow = [
            ("agent-0", "Plan mission"),
            ("agent-1", "Research mission context"),
            ("agent-2", "Produce design/prototype guidance"),
            ("agent-3", "Implement deliverable"),
            ("agent-4", "Review and harden output"),
        ]
        tasks: List[Task] = []
        for agent_id, title in workflow:
            task = Task(
                id=new_id("task"),
                mission_id=mission.id,
                agent_id=agent_id,
                title=title,
                priority=mission.priority,
                details={"mode": mission.mode},
            )
            self.task_repository.create_task(task)
            tasks.append(task)
        self.mission_repository.add_event(mission.id, "workflow_seeded", "planner", "Base workflow seeded", {
            "tasks": [task.id for task in tasks]
        })
        return tasks

    def summary(self) -> dict:
        return {
            "agenda": "advanced",
            "status": "active-scaffold",
            "supports": [
                "backlog",
                "priorities",
                "scheduled_tasks",
                "cooldowns",
                "future_planning",
                "conflict_resolution",
            ],
            "missions": len(self.mission_repository.list_missions()),
        }
