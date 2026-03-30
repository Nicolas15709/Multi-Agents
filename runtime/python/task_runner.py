from dataclasses import dataclass
from typing import Dict, List

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
        if not tasks:
            self.mission_repository.update_mission_status(mission_id, "needs_human")
            self.mission_repository.add_event(
                mission_id,
                "mission_needs_human",
                "system",
                "Mission has no tasks to execute",
                {},
            )
            self.progress_notifier.notify(
                mission_id,
                "blocked",
                "La misión necesita intervención humana porque no tiene tareas ejecutables.",
                {},
            )
            return {"status": "needs_human", "mission_id": mission_id, "reason": "no_tasks"}

        running = [task for task in tasks if task["status"] == "running"]
        blocked = [task for task in tasks if task["status"] == "blocked"]
        failed = [task for task in tasks if task["status"] == "failed"]
        pending = [task for task in tasks if task["status"] == "pending"]
        done = [task for task in tasks if task["status"] == "done"]

        if len(running) > 1:
            for task in running:
                self.agent_state_manager.set_state(
                    task["agent_id"],
                    STATE_BY_AGENT.get(task["agent_id"], "idle"),
                    mission_id=task["mission_id"],
                    task_id=task["id"],
                )
            self.mission_repository.update_mission_status(mission_id, "running")
            return {
                "status": "running",
                "mission_id": mission_id,
                "running_task_ids": [task["id"] for task in running],
                "reason": "multiple_running_tasks_preserved",
            }

        if running:
            task = running[0]
            self.task_repository.update_task_status(task["id"], "done")
            self.mission_repository.add_event(mission_id, "task_completed", task["agent_id"], f"Task completed: {task['title']}", {"task_id": task["id"]})
            self.agent_state_manager.set_state(task["agent_id"], "idle")
            self.progress_notifier.notify(
                mission_id,
                "task_completed",
                f"{task['agent_id']} completó: {task['title']}",
                {"task_id": task["id"], "agent_id": task["agent_id"]},
            )
            tasks = self.task_repository.list_tasks_for_mission(mission_id)
            blocked = [item for item in tasks if item["status"] == "blocked"]
            failed = [item for item in tasks if item["status"] == "failed"]
            pending = [item for item in tasks if item["status"] == "pending"]
            done = [item for item in tasks if item["status"] == "done"]

        if failed:
            self.mission_repository.update_mission_status(mission_id, "needs_human")
            failed_task = failed[0]
            self.agent_state_manager.set_state(failed_task["agent_id"], "blocked", mission_id=mission_id, task_id=failed_task["id"])
            self.mission_repository.add_event(
                mission_id,
                "mission_needs_human",
                failed_task["agent_id"],
                f"Mission needs human intervention after failed task: {failed_task['title']}",
                {"task_id": failed_task["id"], "agent_id": failed_task["agent_id"]},
            )
            self.progress_notifier.notify(
                mission_id,
                "blocked",
                f"La misión requiere ayuda humana tras un fallo en: {failed_task['title']}",
                {"task_id": failed_task["id"], "agent_id": failed_task["agent_id"]},
            )
            return {"status": "needs_human", "mission_id": mission_id, "task_id": failed_task["id"]}

        if blocked and not pending:
            blocked_task = blocked[0]
            self.mission_repository.update_mission_status(mission_id, "blocked")
            self.agent_state_manager.set_state(blocked_task["agent_id"], "blocked", mission_id=mission_id, task_id=blocked_task["id"])
            self.mission_repository.add_event(
                mission_id,
                "mission_blocked",
                blocked_task["agent_id"],
                f"Mission blocked on task: {blocked_task['title']}",
                {"task_id": blocked_task["id"], "agent_id": blocked_task["agent_id"]},
            )
            self.progress_notifier.notify(
                mission_id,
                "blocked",
                f"La misión quedó bloqueada en: {blocked_task['title']}",
                {"task_id": blocked_task["id"], "agent_id": blocked_task["agent_id"]},
            )
            return {"status": "blocked", "mission_id": mission_id, "task_id": blocked_task["id"]}

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

        if len(done) == len(tasks):
            self.mission_repository.update_mission_status(mission_id, "completed")
            self.mission_repository.add_event(mission_id, "mission_completed", "system", "Mission completed successfully", {})
            self.progress_notifier.notify(
                mission_id,
                "mission_completed",
                "La misión se completó correctamente.",
                {},
            )
            return {"status": "completed", "mission_id": mission_id}

        self.mission_repository.update_mission_status(mission_id, "needs_human")
        self.mission_repository.add_event(
            mission_id,
            "mission_needs_human",
            "system",
            "Mission entered an unknown state and needs human review",
            {},
        )
        self.progress_notifier.notify(
            mission_id,
            "blocked",
            "La misión necesita revisión humana por un estado inconsistente.",
            {},
        )
        return {"status": "needs_human", "mission_id": mission_id, "reason": "inconsistent_state"}
