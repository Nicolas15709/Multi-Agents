from dataclasses import dataclass
from typing import Dict, List, Optional

from agent_state import AgentStateManager
from repository import MissionRepository, TaskRepository
from scheduler import Scheduler


@dataclass
class StartupRecoveryService:
    mission_repository: MissionRepository
    task_repository: TaskRepository
    agent_state_manager: AgentStateManager
    scheduler: Scheduler

    def inspect(self) -> Dict:
        return self._recover(apply=False)

    def recover(self) -> Dict:
        return self._recover(apply=True)

    def _recover(self, apply: bool) -> Dict:
        missions = self.mission_repository.list_missions()
        if not missions:
            return {
                "status": "no_missions",
                "focus_mission_id": None,
                "updates": [],
                "counts": {
                    "missions_completed": 0,
                    "missions_requeued": 0,
                    "missions_blocked": 0,
                    "tasks_reset": 0,
                    "agents_reset": 0,
                },
            }

        focus = self.scheduler.highest_priority_mission()
        updates: List[Dict] = []
        counts = {
            "missions_completed": 0,
            "missions_requeued": 0,
            "missions_blocked": 0,
            "tasks_reset": 0,
            "agents_reset": 0,
        }

        for mission in missions:
            mission_id = mission["id"]
            tasks = self.task_repository.list_tasks_for_mission(mission_id)
            running_tasks = [task for task in tasks if task["status"] == "running"]

            if running_tasks:
                for task in running_tasks:
                    if apply:
                        self.task_repository.update_task_status(task["id"], "pending")
                        self.mission_repository.add_event(
                            mission_id,
                            "task_requeued",
                            "system",
                            f"Task re-queued during recovery: {task['title']}",
                            {
                                "task_id": task["id"],
                                "recovery": "startup",
                                "reason": "stale_running_task_after_restart",
                                "was_focus_mission": bool(focus and mission_id == focus["id"]),
                            },
                        )
                        self.agent_state_manager.set_state(task["agent_id"], "idle")
                    counts["tasks_reset"] += 1
                    counts["agents_reset"] += 1
                    updates.append({
                        "mission_id": mission_id,
                        "task_id": task["id"],
                        "action": "task_requeued",
                        "reason": "stale_running_task_after_restart",
                    })

                tasks = self.task_repository.list_tasks_for_mission(mission_id) if apply else [
                    {**task, "status": ("pending" if task["status"] == "running" else task["status"])}
                    for task in tasks
                ]
                running_tasks = []

            pending_tasks = [task for task in tasks if task["status"] == "pending"]
            blocked_tasks = [task for task in tasks if task["status"] == "blocked"]
            done_ids = {task["id"] for task in tasks if task["status"] in {"done", "completed"}}
            ready_tasks = [
                task for task in pending_tasks + blocked_tasks
                if all(dep in done_ids for dep in (task.get("depends_on") or []))
            ]

            if tasks and len(done_ids) == len(tasks) and mission["status"] != "completed":
                if apply:
                    self.mission_repository.update_mission_status(mission_id, "completed")
                    self.mission_repository.add_event(
                        mission_id,
                        "mission_recovered_completed",
                        "system",
                        "Mission marked completed during runtime recovery",
                        {"recovery": "startup", "task_count": len(tasks)},
                    )
                counts["missions_completed"] += 1
                updates.append({"mission_id": mission_id, "action": "mission_completed"})
                continue

            desired_status: Optional[str] = None
            if not tasks:
                desired_status = mission["status"]
            elif running_tasks and focus and mission_id == focus["id"]:
                desired_status = "running"
            elif ready_tasks:
                desired_status = "queued"
            elif pending_tasks or blocked_tasks:
                desired_status = "blocked"
            elif len(done_ids) == len(tasks):
                desired_status = "completed"

            if desired_status and desired_status != mission["status"]:
                if apply:
                    self.mission_repository.update_mission_status(mission_id, desired_status)
                    self.mission_repository.add_event(
                        mission_id,
                        "mission_state_recovered",
                        "system",
                        f"Mission status normalized to {desired_status}",
                        {
                            "recovery": "startup",
                            "previous_status": mission["status"],
                            "next_status": desired_status,
                            "ready_task_count": len(ready_tasks),
                            "running_task_count": len(running_tasks),
                            "blocked_task_count": len(blocked_tasks),
                        },
                    )
                if desired_status == "queued":
                    counts["missions_requeued"] += 1
                elif desired_status == "blocked":
                    counts["missions_blocked"] += 1
                elif desired_status == "completed":
                    counts["missions_completed"] += 1
                updates.append({
                    "mission_id": mission_id,
                    "action": "mission_status_updated",
                    "from": mission["status"],
                    "to": desired_status,
                })

        return {
            "status": "recovered" if apply and updates else ("needs_recovery" if updates else "noop"),
            "focus_mission_id": focus["id"] if focus else None,
            "updates": updates,
            "counts": counts,
        }
