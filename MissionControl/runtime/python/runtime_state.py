from dataclasses import dataclass
from typing import Dict, Optional

from agent_state import AgentStateManager
from repository import MissionRepository, TaskRepository
from scheduler import Scheduler

STATE_BY_AGENT = {
    "agent-0": "planning",
    "agent-1": "researching",
    "agent-2": "designing",
    "agent-3": "building",
    "agent-4": "reviewing",
}


@dataclass
class RuntimeStateHydrator:
    mission_repository: MissionRepository
    task_repository: TaskRepository
    agent_state_manager: AgentStateManager
    scheduler: Optional[Scheduler] = None

    def reconcile(self) -> Dict:
        active_mission = self.scheduler.highest_priority_mission() if self.scheduler else self.mission_repository.get_focus_mission()
        if not active_mission or active_mission["status"] not in self.mission_repository.ACTIVE_STATUSES:
            return {"status": "no_active_missions"}

        tasks = self.task_repository.list_tasks_for_mission(active_mission["id"])
        running_tasks = [task for task in tasks if task["status"] == "running"]
        pending_tasks = [task for task in tasks if task["status"] == "pending"]

        if running_tasks:
            for task in running_tasks:
                self.agent_state_manager.set_state(
                    task["agent_id"],
                    STATE_BY_AGENT.get(task["agent_id"], "idle"),
                    mission_id=task["mission_id"],
                    task_id=task["id"],
                )
            return {"status": "running_tasks_rehydrated", "count": len(running_tasks)}

        if pending_tasks:
            first = pending_tasks[0]
            self.agent_state_manager.set_state(
                first["agent_id"],
                STATE_BY_AGENT.get(first["agent_id"], "idle"),
                mission_id=first["mission_id"],
                task_id=first["id"],
            )
            return {"status": "first_pending_task_marked_active", "task_id": first["id"]}

        return {"status": "nothing_to_rehydrate"}
