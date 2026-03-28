from dataclasses import dataclass
from typing import Dict

from event_stream import EventStreamService
from repository import AgentRepository, MissionRepository, TaskRepository
from utils import utc_now


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
        agents = self.agent_repository.list_agents()
        stream = self.event_stream.snapshot()

        active_agents = [agent for agent in agents if agent.get("state") and agent.get("state") != "idle"]
        completed_tasks = [task for task in active_tasks if task.get("status") in {"done", "completed"}]
        blocked_tasks = [task for task in active_tasks if task.get("status") == "blocked"]

        return {
            "generatedAt": utc_now(),
            "meta": {
                "missionCount": len(missions),
                "agentCount": len(agents),
                "activeAgentCount": len(active_agents),
                "taskCount": len(active_tasks),
                "completedTaskCount": len(completed_tasks),
                "blockedTaskCount": len(blocked_tasks),
                "eventCount": len(stream.get("events", [])),
                "notificationCount": len(stream.get("notifications", [])),
            },
            "missions": missions,
            "activeMission": active_mission,
            "tasks": active_tasks,
            "agents": agents,
            "stream": stream,
        }
