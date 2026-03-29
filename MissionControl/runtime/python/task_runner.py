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

    def _task_ready(self, task: Dict, tasks: List[Dict]) -> bool:
        deps = task.get("depends_on") or []
        if not deps:
            return True
        done_ids = {item["id"] for item in tasks if item["status"] in {"done", "completed"}}
        return all(dep in done_ids for dep in deps)

    def _failed_dependency_ids(self, task: Dict, tasks: List[Dict]) -> List[str]:
        deps = task.get("depends_on") or []
        if not deps:
            return []
        failed_ids = {item["id"] for item in tasks if item["status"] == "failed"}
        return [dep for dep in deps if dep in failed_ids]

    def advance_next_task(self, mission_id: str) -> Dict:
        mission = self.mission_repository.get_mission(mission_id) or {"status": None}
        tasks = self.task_repository.list_tasks_for_mission(mission_id)
        failed_tasks = [task for task in tasks if task["status"] == "failed"]
        if failed_tasks:
            failed_task = failed_tasks[0]
            if mission.get("status") != "needs_human":
                self.mission_repository.update_mission_status(mission_id, "needs_human")
                self.mission_repository.add_event(
                    mission_id,
                    "mission_needs_human",
                    "system",
                    f"Mission requires human attention after task failure: {failed_task['title']}",
                    {
                        "failed_task_id": failed_task["id"],
                        "failed_task_title": failed_task["title"],
                        "failed_agent_id": failed_task["agent_id"],
                    },
                )
                self.progress_notifier.notify(
                    mission_id,
                    "blocked",
                    f"La misión requiere atención humana por una tarea fallida: {failed_task['title']}",
                    {
                        "failed_task_id": failed_task["id"],
                        "failed_agent_id": failed_task["agent_id"],
                    },
                )
            self.agent_state_manager.set_state(failed_task["agent_id"], "blocked", mission_id=mission_id, task_id=failed_task["id"])
            return {
                "status": "needs_human",
                "mission_id": mission_id,
                "failed_task_id": failed_task["id"],
            }

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

        actionable = [task for task in tasks if task["status"] in {"pending", "blocked"}]
        ready = [task for task in actionable if self._task_ready(task, tasks)]
        blocked = [task for task in actionable if task not in ready]

        for task in ready:
            if task["status"] == "blocked":
                self.task_repository.update_task_status(task["id"], "pending")
                self.mission_repository.add_event(
                    mission_id,
                    "task_unblocked",
                    task["agent_id"],
                    f"Task unblocked: {task['title']}",
                    {"task_id": task["id"], "depends_on": task.get("depends_on", [])},
                )

        for task in blocked:
            failed_dependency_ids = self._failed_dependency_ids(task, tasks)
            if failed_dependency_ids:
                if mission.get("status") != "needs_human":
                    self.mission_repository.update_mission_status(mission_id, "needs_human")
                self.mission_repository.add_event(
                    mission_id,
                    "mission_needs_human",
                    "system",
                    f"Mission requires human attention because dependencies failed: {task['title']}",
                    {
                        "task_id": task["id"],
                        "failed_dependency_ids": failed_dependency_ids,
                    },
                )
                self.progress_notifier.notify(
                    mission_id,
                    "blocked",
                    f"La misión requiere atención humana: {task['title']} depende de una tarea fallida.",
                    {"task_id": task["id"], "failed_dependency_ids": failed_dependency_ids},
                )
                return {
                    "status": "needs_human",
                    "mission_id": mission_id,
                    "task_id": task["id"],
                    "failed_dependency_ids": failed_dependency_ids,
                }
            if task["status"] != "blocked":
                self.task_repository.update_task_status(task["id"], "blocked")
                self.mission_repository.add_event(
                    mission_id,
                    "task_blocked",
                    task["agent_id"],
                    f"Task blocked waiting dependencies: {task['title']}",
                    {"task_id": task["id"], "depends_on": task.get("depends_on", [])},
                )
                self.progress_notifier.notify(
                    mission_id,
                    "blocked",
                    f"{task['agent_id']} está bloqueada: {task['title']}",
                    {"task_id": task["id"], "agent_id": task["agent_id"]},
                )

        if ready:
            next_task = ready[0]
            self.task_repository.update_task_status(next_task["id"], "running")
            self.agent_state_manager.set_state(
                next_task["agent_id"],
                STATE_BY_AGENT.get(next_task["agent_id"], "idle"),
                mission_id=mission_id,
                task_id=next_task["id"],
            )
            self.mission_repository.update_mission_status(mission_id, "running")
            self.mission_repository.add_event(mission_id, "task_started", next_task["agent_id"], f"Task started: {next_task['title']}", {"task_id": next_task["id"], "depends_on": next_task.get("depends_on", [])})
            self.progress_notifier.notify(
                mission_id,
                "task_started",
                f"{next_task['agent_id']} inició: {next_task['title']}",
                {"task_id": next_task["id"], "agent_id": next_task["agent_id"]},
            )
            return {"status": "started", "task_id": next_task["id"], "agent_id": next_task["agent_id"]}

        incomplete = [task for task in tasks if task["status"] in {"pending", "blocked", "running"}]
        if incomplete:
            if mission.get("status") != "blocked":
                self.mission_repository.update_mission_status(mission_id, "blocked")
                self.mission_repository.add_event(
                    mission_id,
                    "mission_blocked",
                    "system",
                    "Mission blocked waiting for dependencies",
                    {"blocked_task_ids": [task["id"] for task in incomplete if task["status"] == "blocked"]},
                )
            return {
                "status": "blocked",
                "mission_id": mission_id,
                "blocked_task_ids": [task["id"] for task in incomplete if task["status"] == "blocked"],
            }

        if mission.get("status") != "completed":
            self.mission_repository.update_mission_status(mission_id, "completed")
            self.mission_repository.add_event(mission_id, "mission_completed", "system", "Mission completed successfully", {})
            self.progress_notifier.notify(
                mission_id,
                "mission_completed",
                "La misión se completó correctamente.",
                {},
            )
        return {"status": "completed", "mission_id": mission_id}
