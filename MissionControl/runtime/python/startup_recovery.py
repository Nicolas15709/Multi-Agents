"""Startup recovery service using state reconciler and robust detection."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from agent_state import AgentStateManager
from repository import MissionRepository, TaskRepository
from scheduler import Scheduler
from state_machine import StateReconciler, TransactionalStateUpdater


@dataclass
class StartupRecoveryService:
    mission_repository: MissionRepository
    task_repository: TaskRepository
    agent_state_manager: AgentStateManager
    scheduler: Scheduler
    state_updater: Optional[TransactionalStateUpdater] = None
    state_reconciler: Optional[StateReconciler] = None

    def inspect(self) -> Dict:
        """Inspect recovery needs without applying changes."""
        return self._recover(apply=False)

    def recover(self) -> Dict:
        """Perform full recovery and state normalization."""
        return self._recover(apply=True)

    def _recover(self, apply: bool) -> Dict:
        """Core recovery logic."""
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
                "reconciler_details": None,
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

        # Phase 1: Use StateReconciler to normalize mission states based on task states
        reconciler_details = None
        if self.state_reconciler:
            reconciler_result = self.state_reconciler.reconcile_mission_states(apply=apply)
            reconciler_details = reconciler_result
            counts["missions_requeued"] += reconciler_result.get("fixes_applied", 0)
            # Collect details
            for detail in reconciler_result.get("details", []):
                updates.append({
                    "mission_id": detail["mission_id"],
                    "action": "mission_status_normalized",
                    "from": detail["from"],
                    "to": detail["to"],
                    "method": "state_reconciler",
                })

        # Phase 2: Handling for stale running tasks after restart
        # (StateReconciler doesn't automatically reset running tasks to pending)
        for mission in missions:
            mission_id = mission["id"]
            tasks = self.task_repository.list_tasks_for_mission(mission_id)
            running_tasks = [task for task in tasks if task["status"] == "running"]

            if running_tasks:
                for task in running_tasks:
                    if apply:
                        # Use state_updater for atomic transition if available
                        if self.state_updater:
                            try:
                                self.state_updater.begin_transaction()
                                self.state_updater.transition_task(
                                    task["id"],
                                    "pending",
                                    reason="startup_recovery_stale_task",
                                    actor="startup_recovery"
                                )
                                self.state_updater.commit_transaction()
                            except Exception:
                                self.state_updater.rollback_transaction()
                                raise
                        else:
                            self.task_repository.update_task_status(task["id"], "pending")
                        # Reset agent to idle
                        self.agent_state_manager.set_state(task["agent_id"], "idle")
                    counts["tasks_reset"] += 1
                    counts["agents_reset"] += 1
                    updates.append({
                        "mission_id": mission_id,
                        "task_id": task["id"],
                        "action": "task_reset_from_running",
                        "reason": "stale_running_task_after_restart",
                        "was_focus_mission": bool(focus and mission_id == focus["id"]),
                    })

        # Phase 3: Ensure focus mission has a consistent state
        if focus:
            focus_id = focus["id"]
            focus_tasks = self.task_repository.list_tasks_for_mission(focus_id)
            # After recovery, focus mission should be either queued (has ready tasks) or running (has running tasks)
            # We trust the scheduler's highest_priority_mission but ensure it's not in an invalid state
            focus_status = focus["status"]
            if focus_status == "completed":
                # Completed missions are fine
                pass
            elif focus_status in {"queued", "running", "blocked"}:
                # These are acceptable
                pass
            else:
                # Unknown status, attempt to normalize via reconciler or set to queued
                if apply and self.state_updater:
                    try:
                        self.state_updater.begin_transaction()
                        self.state_updater.transition_mission(
                            focus_id,
                            "queued",
                            reason="normalize_focus_mission",
                            actor="startup_recovery"
                        )
                        self.state_updater.commit_transaction()
                        counts["missions_requeued"] += 1
                        updates.append({
                            "mission_id": focus_id,
                            "action": "focus_mission_normalized",
                            "from": focus_status,
                            "to": "queued",
                        })
                    except Exception:
                        self.state_updater.rollback_transaction()

        # Determine overall status
        if apply and updates:
            status = "recovered"
        elif updates:
            status = "needs_recovery"
        else:
            status = "noop"

        return {
            "status": status,
            "focus_mission_id": focus["id"] if focus else None,
            "updates": updates,
            "counts": counts,
            "reconciler_details": reconciler_details,
        }
