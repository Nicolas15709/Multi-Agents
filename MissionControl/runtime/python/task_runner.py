"""Task execution runner with state machine validation."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from agent_state import AgentStateManager
from progress import ProgressNotifier
from repository import MissionRepository, TaskRepository
from state_machine import TaskStateMachine, StateValidationError, TransactionalStateUpdater

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
    state_updater: Optional[TransactionalStateUpdater] = None

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

    def _transition_task_with_validation(self, task_id: str, to_status: str, reason: Optional[str] = None, actor: Optional[str] = None) -> bool:
        """Transition a task using state_updater if available, with validation."""
        if self.state_updater:
            try:
                self.state_updater.begin_transaction()
                self.state_updater.transition_task(task_id, to_status, reason=reason, actor=actor)
                self.state_updater.commit_transaction()
                return True
            except StateValidationError:
                self.state_updater.rollback_transaction()
                raise
        else:
            # Legacy: direct update without validation
            self.task_repository.update_task_status(task_id, to_status)
            return True

    def advance_next_task(self, mission_id: str) -> Dict:
        mission = self.mission_repository.get_mission(mission_id) or {"status": None}
        tasks = self.task_repository.list_tasks_for_mission(mission_id)
        failed_tasks = [task for task in tasks if task["status"] == "failed"]
        if failed_tasks:
            failed_task = failed_tasks[0]
            if mission.get("status") != "needs_human":
                # Transition mission to needs_human using state machine if possible
                if self.state_updater:
                    try:
                        self.state_updater.begin_transaction()
                        self.state_updater.transition_mission(
                            mission_id,
                            "needs_human",
                            reason="task_failed",
                            actor="task_runner"
                        )
                        self.state_updater.commit_transaction()
                    except StateValidationError:
                        self.state_updater.rollback_transaction()
                        raise
                else:
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
            self.agent_state_manager.set_state(
                failed_task["agent_id"],
                "blocked",
                mission_id=mission_id,
                task_id=failed_task["id"]
            )
            return {
                "status": "needs_human",
                "mission_id": mission_id,
                "failed_task_id": failed_task["id"],
            }

        running = [task for task in tasks if task["status"] == "running"]
        if running:
            task = running[0]
            # Transition task to done
            self._transition_task_with_validation(
                task["id"],
                "done",
                reason="task_completed",
                actor="task_runner"
            )
            self.mission_repository.add_event(
                mission_id,
                "task_completed",
                task["agent_id"],
                f"Task completed: {task['title']}",
                {"task_id": task["id"], "task_title": task["title"]}
            )
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
                self._transition_task_with_validation(
                    task["id"],
                    "pending",
                    reason="dependencies_met",
                    actor="task_runner"
                )
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
                    if self.state_updater:
                        try:
                            self.state_updater.begin_transaction()
                            self.state_updater.transition_mission(
                                mission_id,
                                "needs_human",
                                reason="dependency_failed",
                                actor="task_runner"
                            )
                            self.state_updater.commit_transaction()
                        except StateValidationError:
                            self.state_updater.rollback_transaction()
                            raise
                    else:
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
                self._transition_task_with_validation(
                    task["id"],
                    "blocked",
                    reason="waiting_dependencies",
                    actor="task_runner"
                )
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
            # Transition task to running
            self._transition_task_with_validation(
                next_task["id"],
                "running",
                reason="task_started",
                actor="task_runner"
            )
            self.agent_state_manager.set_state(
                next_task["agent_id"],
                STATE_BY_AGENT.get(next_task["agent_id"], "idle"),
                mission_id=mission_id,
                task_id=next_task["id"],
            )
            # Transition mission to running
            if self.state_updater:
                try:
                    self.state_updater.begin_transaction()
                    self.state_updater.transition_mission(
                        mission_id,
                        "running",
                        reason="task_started",
                        actor="task_runner"
                    )
                    self.state_updater.commit_transaction()
                except StateValidationError:
                    self.state_updater.rollback_transaction()
                    raise
            else:
                self.mission_repository.update_mission_status(mission_id, "running")
            self.mission_repository.add_event(
                mission_id,
                "task_started",
                next_task["agent_id"],
                f"Task started: {next_task['title']}",
                {"task_id": next_task["id"], "depends_on": next_task.get("depends_on", [])}
            )
            self.progress_notifier.notify(
                mission_id,
                "task_started",
                f"{next_task['agent_id']} inició: {next_task['title']}",
                {"task_id": next_task["id"], "agent_id": next_task["agent_id"]},
            )
            return {"status": "started", "task_id": next_task["id"], "agent_id": next_task["agent_id"]}

        incomplete = [task for task in tasks if task["status"] in {"pending", "blocked", "running"}]
        if incomplete:
            # Mission should be blocked (or queued if no running tasks)
            desired_status = "blocked" if any(t["status"] == "blocked" for t in incomplete) else "queued"
            if mission.get("status") != desired_status:
                if self.state_updater:
                    try:
                        self.state_updater.begin_transaction()
                        self.state_updater.transition_mission(
                            mission_id,
                            desired_status,
                            reason="tasks_incomplete",
                            actor="task_runner"
                        )
                        self.state_updater.commit_transaction()
                    except StateValidationError:
                        self.state_updater.rollback_transaction()
                        raise
                else:
                    self.mission_repository.update_mission_status(mission_id, desired_status)
                self.mission_repository.add_event(
                    mission_id,
                    "mission_blocked" if desired_status == "blocked" else "mission_queued",
                    "system",
                    f"Mission {desired_status} waiting for dependencies",
                    {"blocked_task_ids": [task["id"] for task in incomplete if task["status"] == "blocked"]} if desired_status == "blocked" else {},
                )
            return {
                "status": desired_status,
                "mission_id": mission_id,
                "blocked_task_ids": [task["id"] for task in incomplete if task["status"] == "blocked"] if desired_status == "blocked" else [],
            }

        # All tasks are in terminal states (done/completed)
        if mission.get("status") != "completed":
            if self.state_updater:
                try:
                    self.state_updater.begin_transaction()
                    self.state_updater.transition_mission(
                        mission_id,
                        "completed",
                        reason="all_tasks_finished",
                        actor="task_runner"
                    )
                    self.state_updater.commit_transaction()
                except StateValidationError:
                    self.state_updater.rollback_transaction()
                    raise
            else:
                self.mission_repository.update_mission_status(mission_id, "completed")
            self.mission_repository.add_event(
                mission_id,
                "mission_completed",
                "system",
                "Mission completed successfully",
                {}
            )
            self.progress_notifier.notify(
                mission_id,
                "mission_completed",
                "La misión se completó correctamente.",
                {},
            )
        return {"status": "completed", "mission_id": mission_id}
