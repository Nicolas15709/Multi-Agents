from dataclasses import dataclass
from typing import Dict, List, Optional

from models import Mission, Task
from repository import MissionRepository, TaskRepository
from templates import TemplateRegistry
from utils import new_id

DEFAULT_WORKFLOW = [
    ("agent-0", "Plan mission"),
    ("agent-1", "Research mission context"),
    ("agent-2", "Produce design/prototype guidance"),
    ("agent-3", "Implement deliverable"),
    ("agent-4", "Review and harden output"),
]

TASK_TITLE_BY_AGENT = {
    "agent-0": "Plan mission",
    "agent-1": "Research mission context",
    "agent-2": "Produce design/prototype guidance",
    "agent-3": "Implement deliverable",
    "agent-4": "Review and harden output",
}


@dataclass
class Planner:
    config: object
    mission_repository: MissionRepository
    task_repository: TaskRepository
    template_registry: Optional[TemplateRegistry] = None
    thought_log: Optional[ThoughtLogService] = None

    def create_mission(self, title: str, goal: str, mode: str, priority: str = "medium", source: str = "manual", allow_24x7: bool = False) -> Mission:
        if self.thought_log:
            self.thought_log.record(
                "bootstrap",
                "create_mission",
                f"Planning mission '{title}'",
                {"mode": mode, "priority": priority, "source": source},
            )
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

    def _workflow_for_mode(self, mode: str) -> List[tuple]:
        if self.template_registry:
            try:
                template = self.template_registry.get_template(mode)
                agents = template.get("primaryAgents", [])
                workflow = []
                for agent_id in agents:
                    workflow.append((agent_id, TASK_TITLE_BY_AGENT.get(agent_id, f"Execute {mode} task")))
                if workflow:
                    return workflow
            except KeyError:
                pass
        return DEFAULT_WORKFLOW

    def seed_base_workflow(self, mission: Mission) -> List[Task]:
        workflow = self._workflow_for_mode(mission.mode)
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
            "tasks": [task.id for task in tasks],
            "mode": mission.mode,
            "agents": [task.agent_id for task in tasks],
        })
        if self.thought_log:
            self.thought_log.record(
                mission.id,
                "seed_base_workflow",
                "Base workflow seeded for mission",
                {
                    "workflow_length": len(tasks),
                    "agents": [task.agent_id for task in tasks],
                },
            )
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
                "template_seeded_workflows",
            ],
            "missions": len(self.mission_repository.list_missions()),
        }
