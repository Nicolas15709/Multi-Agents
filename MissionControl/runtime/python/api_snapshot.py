from dataclasses import dataclass
from typing import Dict, Optional

from event_stream import EventStreamService
from repository import AgentRepository, MissionRepository, TaskRepository
from progress_summary import ProgressSummaryService
from mission_summary import MissionSummaryService
from scheduler import Scheduler
from utils import utc_now


@dataclass
class RuntimeSnapshotAPI:
    mission_repository: MissionRepository
    task_repository: TaskRepository
    agent_repository: AgentRepository
    event_stream: EventStreamService
    progress_summary: Optional[ProgressSummaryService] = None
    mission_summary: Optional[MissionSummaryService] = None
    scheduler: Optional[Scheduler] = None

    def snapshot(self) -> Dict:
        missions = self.mission_repository.list_missions()
        active_mission = self.scheduler.highest_priority_mission() if self.scheduler else self.mission_repository.get_focus_mission()
        active_tasks = self.task_repository.list_tasks_for_mission(active_mission["id"]) if active_mission else []
        agents = self.agent_repository.list_agents()
        stream = self.event_stream.snapshot()

        active_agents = [agent for agent in agents if agent.get("state") and agent.get("state") != "idle"]
        completed_tasks = [task for task in active_tasks if task.get("status") in {"done", "completed"}]
        blocked_tasks = [task for task in active_tasks if task.get("status") == "blocked"]
        failed_tasks = [task for task in active_tasks if task.get("status") == "failed"]
        running_task = next((task for task in active_tasks if task.get("status") == "running"), None)

        progress = self.progress_summary.latest() if self.progress_summary else {"mission": None, "progress": {"total": 0, "done": 0, "running": 0, "blocked": 0, "failed": 0, "percent": 0}}
        mission_summary = self.mission_summary.build(progress["mission"]["id"]) if self.mission_summary and progress.get("mission") else None
        return {
            "generatedAt": utc_now(),
            "progress": progress,
            "missionSummary": mission_summary,
            "meta": {
                "missionCount": len(missions),
                "agentCount": len(agents),
                "activeAgentCount": len(active_agents),
                "taskCount": len(active_tasks),
                "completedTaskCount": len(completed_tasks),
                "blockedTaskCount": len(blocked_tasks),
                "failedTaskCount": len(failed_tasks),
                "eventCount": len(stream.get("events", [])),
                "notificationCount": len(stream.get("notifications", [])),
                "runningTaskId": running_task.get("id") if running_task else None,
                "runningTaskTitle": running_task.get("title") if running_task else None,
            },
            "missions": missions,
            "activeMission": active_mission,
            "tasks": active_tasks,
            "agents": agents,
            "stream": stream,
        }
