from dataclasses import dataclass
from typing import Dict

from agent_state import AgentStateManager
from repository import MissionRepository, TaskRepository

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

    def reconcile(self) -> Dict:
        missions = self.mission_repository.list_missions()
        active = [m for m in missions if m["status"] in {"queued", "running", "blocked", "needs_human"}]
        if not active:
            return {"status": "no_active_missions"}

        active_mission = active[0]
        tasks = self.task_repository.list_tasks_for_mission(active_mission["id"])
        running_tasks = [task for task in tasks if task["status"] == "running"]
        blocked_tasks = [task for task in tasks if task["status"] == "blocked"]
        failed_tasks = [task for task in tasks if task["status"] == "failed"]
        pending_tasks = [task for task in tasks if task["status"] == "pending"]
        done_tasks = [task for task in tasks if task["status"] == "done"]

        if running_tasks:
            self.mission_repository.update_mission_status(active_mission["id"], "running")
            for task in running_tasks:
                self.agent_state_manager.set_state(
                    task["agent_id"],
                    STATE_BY_AGENT.get(task["agent_id"], "idle"),
                    mission_id=task["mission_id"],
                    task_id=task["id"],
                )
            return {"status": "running_tasks_rehydrated", "count": len(running_tasks)}

        if failed_tasks:
            failed_task = failed_tasks[0]
            self.mission_repository.update_mission_status(active_mission["id"], "needs_human")
            self.agent_state_manager.set_state(
                failed_task["agent_id"],
                "blocked",
                mission_id=failed_task["mission_id"],
                task_id=failed_task["id"],
            )
            return {"status": "failed_task_requires_human", "task_id": failed_task["id"]}

        if blocked_tasks and not pending_tasks:
            blocked_task = blocked_tasks[0]
            self.mission_repository.update_mission_status(active_mission["id"], "blocked")
            self.agent_state_manager.set_state(
                blocked_task["agent_id"],
                "blocked",
                mission_id=blocked_task["mission_id"],
                task_id=blocked_task["id"],
            )
            return {"status": "blocked_task_rehydrated", "task_id": blocked_task["id"]}

        if pending_tasks:
            self.mission_repository.update_mission_status(active_mission["id"], "queued")
            first = pending_tasks[0]
            self.agent_state_manager.set_state(
                first["agent_id"],
                STATE_BY_AGENT.get(first["agent_id"], "idle"),
                mission_id=first["mission_id"],
                task_id=first["id"],
            )
            return {"status": "first_pending_task_marked_active", "task_id": first["id"]}

        if tasks and len(done_tasks) == len(tasks):
            self.mission_repository.update_mission_status(active_mission["id"], "completed")
            return {"status": "mission_already_completed", "mission_id": active_mission["id"]}

        return {"status": "nothing_to_rehydrate", "mission_id": active_mission["id"]}
