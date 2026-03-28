from dataclasses import dataclass
from typing import Dict, List, Optional

from agent_state import AgentStateManager
from progress import ProgressNotifier
from repository import MissionRepository, TaskRepository

STATE_BY_AGENT = {
    "agent-0": "planning",
    "agent-1": "researching",
    "agent-2": "designing",
    "agent-3": "building",
    "agent-4": "reviewing",
}


@dataclass
class TaskRunner:
    mission_repository: MissionRepository
    task_repository: TaskRepository
    agent_state_manager: AgentStateManager
    progress_notifier: ProgressNotifier

    def advance_next_task(self, mission_id: str) -> Dict:
        tasks = self.task_repository.list_tasks_for_mission(mission_id)
        running = [task for task in tasks if task["status"] == "running"]
        if running:
            task = running[0]
            self.task_repository.update_task_status(task["id"], "done")
            self.mission_repository.add_event(mission_id, "task_completed", task["agent_id"], f"Task completed: {task['title']}", {"task_id": task["id"], "task_title": task["title"]})
            self.agent_state_manager.set_state(task["agent_id"], "idle")
            self.progress_notifier.notify(
                mission_id,
                "task_completed",
                f"{task['agent_id']} completó: {task['title']}",
                {"task_id": task["id"], "agent_id": task["agent_id"]},
            )
            tasks = self.task_repository.list_tasks_for_mission(mission_id)

        pending = [task for task in tasks if task["status"] == "pending"]
        if pending:
            next_task = pending[0]
            self.task_repository.update_task_status(next_task["id"], "running")
            self.agent_state_manager.set_state(
                next_task["agent_id"],
                STATE_BY_AGENT.get(next_task["agent_id"], "idle"),
                mission_id=mission_id,
                task_id=next_task["id"],
            )
            self.mission_repository.update_mission_status(mission_id, "running")
            self.mission_repository.add_event(mission_id, "task_started", next_task["agent_id"], f"Task started: {next_task['title']}", {"task_id": next_task["id"]})
            self.progress_notifier.notify(
                mission_id,
                "task_started",
                f"{next_task['agent_id']} inició: {next_task['title']}",
                {"task_id": next_task["id"], "agent_id": next_task["agent_id"]},
            )
            return {"status": "started", "task_id": next_task["id"], "agent_id": next_task["agent_id"]}

        self.mission_repository.update_mission_status(mission_id, "completed")
        self.mission_repository.add_event(mission_id, "mission_completed", "system", "Mission completed successfully", {})
        self.progress_notifier.notify(
            mission_id,
            "mission_completed",
            "La misión se completó correctamente.",
            {},
        )
        return {"status": "completed", "mission_id": mission_id}
