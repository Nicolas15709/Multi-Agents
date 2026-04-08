from dataclasses import dataclass
from typing import Dict, Optional

try:
    from .event_stream import EventStreamService
    from .repository import (
        ActionApprovalRepository,
        AgentHireRequestRepository,
        AgentMessageRepository,
        AgentRepository,
        IntakeRequestRepository,
        MissionControlRepository,
        MissionMemoryRepository,
        MissionRepository,
        TaskRepository,
    )
    from .progress_summary import ProgressSummaryService
    from .mission_summary import MissionSummaryService
    from .scheduler import Scheduler
    from .utils import utc_now
except ImportError:  # pragma: no cover - runtime script compatibility
    from event_stream import EventStreamService
    from repository import (
        ActionApprovalRepository,
        AgentHireRequestRepository,
        AgentMessageRepository,
        AgentRepository,
        IntakeRequestRepository,
        MissionControlRepository,
        MissionMemoryRepository,
        MissionRepository,
        TaskRepository,
    )
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
    intake_repository: Optional[IntakeRequestRepository] = None
    hire_request_repository: Optional[AgentHireRequestRepository] = None
    mission_control_repository: Optional[MissionControlRepository] = None
    mission_memory_repository: Optional[MissionMemoryRepository] = None
    agent_message_repository: Optional[AgentMessageRepository] = None
    action_approval_repository: Optional[ActionApprovalRepository] = None

    def snapshot(self) -> Dict:
        missions = self.mission_repository.list_missions()
        mission_summaries = (
            {
                mission["id"]: self.mission_summary.build(mission["id"])
                for mission in missions
            }
            if self.mission_summary
            else {}
        )
        mission_controls_by_id = (
            self.mission_control_repository.list_controls_for_missions([mission["id"] for mission in missions])
            if self.mission_control_repository and missions
            else {}
        )
        missions = [
            {
                **mission,
                "mission_control": mission_controls_by_id.get(mission["id"]),
            }
            for mission in missions
        ]
        active_mission = self.scheduler.highest_priority_mission() if self.scheduler else self.mission_repository.get_focus_mission()
        active_tasks = self.task_repository.list_tasks_for_mission(active_mission["id"]) if active_mission else []
        agents = self.agent_repository.list_agents()
        intake_requests = self.intake_repository.list_requests(limit=20) if self.intake_repository else []
        hire_requests = (
            self.hire_request_repository.list_requests_for_mission(active_mission["id"])
            if self.hire_request_repository and active_mission
            else []
        )
        shared_memory = (
            self.mission_memory_repository.list_recent(active_mission["id"], limit=20)
            if self.mission_memory_repository and active_mission
            else []
        )
        agent_messages = (
            self.agent_message_repository.list_messages_for_mission(active_mission["id"], limit=30)
            if self.agent_message_repository and active_mission
            else []
        )
        action_approvals = (
            self.action_approval_repository.list_for_mission(active_mission["id"], limit=30)
            if self.action_approval_repository and active_mission
            else []
        )
        mission_control = (
            self.mission_control_repository.get_control(active_mission["id"])
            if self.mission_control_repository and active_mission
            else None
        )
        stream = self.event_stream.snapshot()

        active_agents = [agent for agent in agents if agent.get("state") and agent.get("state") != "idle"]
        completed_tasks = [task for task in active_tasks if task.get("status") in {"done", "completed"}]
        blocked_tasks = [task for task in active_tasks if task.get("status") == "blocked"]
        failed_tasks = [task for task in active_tasks if task.get("status") == "failed"]
        pending_requests = [request for request in intake_requests if request.get("status") == "pending"]
        running_task = next((task for task in active_tasks if task.get("status") == "running"), None)

        progress = self.progress_summary.latest() if self.progress_summary else {"mission": None, "progress": {"total": 0, "done": 0, "running": 0, "blocked": 0, "failed": 0, "percent": 0}}
        mission_summary = mission_summaries.get(progress["mission"]["id"]) if progress.get("mission") else None
        return {
            "generatedAt": utc_now(),
            "progress": progress,
            "missionSummary": mission_summary,
            "missionSummaries": mission_summaries,
            "scheduler": self.scheduler.summary() if self.scheduler else {},
            "meta": {
                "missionCount": len(missions),
                "agentCount": len(agents),
                "activeAgentCount": len(active_agents),
                "taskCount": len(active_tasks),
                "completedTaskCount": len(completed_tasks),
                "blockedTaskCount": len(blocked_tasks),
                "failedTaskCount": len(failed_tasks),
                "intakeRequestCount": len(intake_requests),
                "pendingIntakeCount": len(pending_requests),
                "hireRequestCount": len(hire_requests),
                "sharedMemoryCount": len(shared_memory),
                "agentMessageCount": len(agent_messages),
                "actionApprovalCount": len(action_approvals),
                "eventCount": len(stream.get("events", [])),
                "notificationCount": len(stream.get("notifications", [])),
                "runningTaskId": running_task.get("id") if running_task else None,
                "runningTaskTitle": running_task.get("title") if running_task else None,
                "activeMissionBudgetStatus": mission_control.get("status") if mission_control else None,
            },
            "missions": missions,
            "activeMission": active_mission,
            "activeMissionControl": mission_control,
            "tasks": active_tasks,
            "agents": agents,
            "intakeRequests": intake_requests,
            "hireRequests": hire_requests,
            "sharedMemory": shared_memory,
            "agentMessages": agent_messages,
            "actionApprovals": action_approvals,
            "stream": stream,
        }
