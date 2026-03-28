from dataclasses import dataclass
from typing import Dict

from event_stream import EventStreamService
from repository import AgentRepository, MissionRepository, TaskRepository


@dataclass
class RuntimeSnapshotAPI:
    mission_repository: MissionRepository
    task_repository: TaskRepository
    agent_repository: AgentRepository
    event_stream: EventStreamService

    def snapshot(self) -> Dict:
        missions = self.mission_repository.list_missions()
        active_mission = missions[0] if missions else None
        active_tasks = self.task_repository.list_tasks_for_mission(active_mission["id"]) if active_mission else []
        return {
            "missions": missions,
            "activeMission": active_mission,
            "tasks": active_tasks,
            "agents": self.agent_repository.list_agents(),
            "stream": self.event_stream.snapshot(),
        }
