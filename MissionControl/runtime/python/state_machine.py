"""Mission State Machine - Centralized state transition management."""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .models import MissionStatus, TaskStatus, AgentState
from .repository import MissionRepository, TaskRepository
from .utils import utc_now


class StateValidationError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class MissionStateMachine:
    """Finite state machine for mission lifecycle management."""

    # Valid transitions: from_state -> [to_states]
    VALID_TRANSITIONS = {
        "queued": ["running", "blocked", "needs_human", "completed"],
        "running": ["queued", "blocked", "needs_human", "completed"],
        "blocked": ["queued", "running", "needs_human"],
        "needs_human": ["queued", "running", "completed"],
        "completed": [],  # Terminal state
    }

    @classmethod
    def validate_transition(cls, from_status: str, to_status: str) -> bool:
        """Check if a state transition is valid."""
        if from_status not in cls.VALID_TRANSITIONS:
            return False
        return to_status in cls.VALID_TRANSITIONS[from_status]

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """Public method to check if transition is allowed."""
        return cls.validate_transition(from_status, to_status)

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """Check if a status is terminal (no further transitions)."""
        return status == "completed"

    @classmethod
    def get_allowed_transitions(cls, from_status: str) -> List[str]:
        """Get list of allowed next states."""
        return cls.VALID_TRANSITIONS.get(from_status, [])


class TaskStateMachine:
    """Finite state machine for task lifecycle management."""

    VALID_TRANSITIONS = {
        "pending": ["running", "blocked", "failed"],
        "running": ["done", "failed", "blocked"],
        "blocked": ["pending", "failed"],
        "failed": ["pending"],  # Retry allowed
        "done": [],  # Terminal state
    }

    @classmethod
    def validate_transition(cls, from_status: str, to_status: str) -> bool:
        if from_status not in cls.VALID_TRANSITIONS:
            return False
        return to_status in cls.VALID_TRANSITIONS[from_status]

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        return cls.validate_transition(from_status, to_status)

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        return status == "done"

    @classmethod
    def get_allowed_transitions(cls, from_status: str) -> List[str]:
        return cls.VALID_TRANSITIONS.get(from_status, [])


class AgentStateMachine:
    """Finite state machine for agent state management."""

    VALID_TRANSITIONS = {
        "idle": ["planning", "researching", "designing", "building", "reviewing", "blocked"],
        "planning": ["idle", "blocked"],
        "researching": ["idle", "blocked"],
        "designing": ["idle", "blocked"],
        "building": ["idle", "blocked"],
        "reviewing": ["idle", "blocked"],
        "blocked": ["idle"],  # Can recover from blocked state
    }

    @classmethod
    def validate_transition(cls, from_status: str, to_status: str) -> bool:
        if from_status not in cls.VALID_TRANSITIONS:
            return False
        return to_status in cls.VALID_TRANSITIONS[from_status]

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        return cls.validate_transition(from_status, to_status)

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        return False  # No terminal states for agents

    @classmethod
    def get_allowed_transitions(cls, from_status: str) -> List[str]:
        return cls.VALID_TRANSITIONS.get(from_status, [])


@dataclass
class StateTransition:
    """Record of a state transition."""
    entity_type: str  # 'mission', 'task', 'agent'
    entity_id: str
    from_status: str
    to_status: str
    timestamp: str = field(default_factory=utc_now)
    reason: Optional[str] = None
    actor: Optional[str] = None


@dataclass
class StateHistory:
    """Audit trail for state changes."""
    transitions: List[StateTransition] = field(default_factory=list)

    def record(self, transition: StateTransition) -> None:
        self.transitions.append(transition)

    def get_history(self, entity_id: str, entity_type: Optional[str] = None) -> List[StateTransition]:
        """Get transition history for an entity."""
        result = []
        for t in self.transitions:
            if t.entity_id == entity_id:
                if entity_type is None or t.entity_type == entity_type:
                    result.append(t)
        return sorted(result, key=lambda x: x.timestamp)

    def get_latest(self, entity_id: str, entity_type: str) -> Optional[StateTransition]:
        """Get the most recent transition for an entity."""
        history = self.get_history(entity_id, entity_type)
        return history[-1] if history else None


class TransactionalStateUpdater:
    """Manages atomic state transitions across multiple repositories."""

    def __init__(
        self,
        mission_repository: MissionRepository,
        task_repository: TaskRepository,
        state_history: StateHistory
    ):
        self.mission_repository = mission_repository
        self.task_repository = task_repository
        self.state_history = state_history
        self._pending_transitions: List[StateTransition] = []

    def begin_transaction(self) -> None:
        """Start a new transaction batch."""
        self._pending_transitions = []

    def commit_transaction(self) -> None:
        """Commit all pending transitions to history."""
        for transition in self._pending_transitions:
            self.state_history.record(transition)
        self._pending_transitions = []

    def rollback_transaction(self) -> None:
        """Cancel pending transitions."""
        self._pending_transitions = []

    def transition_mission(
        self,
        mission_id: str,
        to_status: str,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
        validate: bool = True
    ) -> bool:
        """Transition a mission to a new status with validation."""
        mission = self.mission_repository.get_mission(mission_id)
        if not mission:
            return False

        from_status = mission["status"]

        if validate and not MissionStateMachine.can_transition(from_status, to_status):
            raise StateValidationError(
                f"Invalid mission state transition: {from_status} -> {to_status}"
            )

        # Execute transition
        self.mission_repository.update_mission_status(mission_id, to_status)

        # Record in pending transactions
        transition = StateTransition(
            entity_type="mission",
            entity_id=mission_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            actor=actor,
        )
        self._pending_transitions.append(transition)

        return True

    def transition_task(
        self,
        task_id: str,
        to_status: str,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
        validate: bool = True
    ) -> bool:
        """Transition a task to a new status with validation."""
        task = self.task_repository.get_task(task_id)
        if not task:
            return False

        from_status = task["status"]

        if validate and not TaskStateMachine.can_transition(from_status, to_status):
            raise StateValidationError(
                f"Invalid task state transition: {from_status} -> {to_status}"
            )

        # Execute transition
        self.task_repository.update_task_status(task_id, to_status)

        # Record in pending transactions
        transition = StateTransition(
            entity_type="task",
            entity_id=task_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            actor=actor,
        )
        self._pending_transitions.append(transition)

        return True

    def get_entity_history(
        self,
        entity_id: str,
        entity_type: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Get state transition history for an entity."""
        transitions = self.state_history.get_history(entity_id, entity_type)
        if limit:
            transitions = transitions[-limit:]
        return [
            {
                "from_status": t.from_status,
                "to_status": t.to_status,
                "timestamp": t.timestamp,
                "reason": t.reason,
                "actor": t.actor,
            }
            for t in transitions
        ]


class StateReconciler:
    """Reconciles state inconsistencies across the system."""

    def __init__(
        self,
        mission_repository: MissionRepository,
        task_repository: TaskRepository,
        state_updater: TransactionalStateUpdater
    ):
        self.mission_repository = mission_repository
        self.task_repository = task_repository
        self.state_updater = state_updater

    def reconcile_mission_states(self, apply: bool = False) -> Dict:
        """Check and fix inconsistent mission states."""
        missions = self.mission_repository.list_missions()
        results = {
            "missions_checked": len(missions),
            "inconsistencies_found": 0,
            "fixes_applied": 0,
            "details": [],
        }

        for mission in missions:
            mission_id = mission["id"]
            tasks = self.task_repository.list_tasks_for_mission(mission_id)

            # Count task statuses
            done_tasks = [t for t in tasks if t["status"] in {"done", "completed"}]
            running_tasks = [t for t in tasks if t["status"] == "running"]
            pending_tasks = [t for t in tasks if t["status"] == "pending"]
            blocked_tasks = [t for t in tasks if t["status"] == "blocked"]

            expected_status = self._infer_mission_status(mission, tasks, done_tasks, running_tasks, pending_tasks, blocked_tasks)

            if expected_status != mission["status"]:
                results["inconsistencies_found"] += 1
                if apply:
                    try:
                        self.state_updater.begin_transaction()
                        self.state_updater.transition_mission(
                            mission_id,
                            expected_status,
                            reason="auto_reconciliation",
                            actor="state_reconciler"
                        )
                        self.state_updater.commit_transaction()
                        results["fixes_applied"] += 1
                        results["details"].append({
                            "mission_id": mission_id,
                            "title": mission["title"],
                            "from": mission["status"],
                            "to": expected_status,
                        })
                    except Exception as e:
                        results["details"].append({
                            "mission_id": mission_id,
                            "error": str(e),
                        })
                        self.state_updater.rollback_transaction()

        return results

    def _infer_mission_status(
        self,
        mission: Dict,
        tasks: List[Dict],
        done_tasks: List[Dict],
        running_tasks: List[Dict],
        pending_tasks: List[Dict],
        blocked_tasks: List[Dict]
    ) -> str:
        """Infer the correct mission status based on task states."""
        if not tasks:
            return mission["status"]

        # If all tasks are done, mission should be completed
        if len(done_tasks) == len(tasks):
            return "completed"

        # If there are running tasks, mission should be running
        if running_tasks:
            return "running"

        # If there are blocked tasks or pending tasks with unmet dependencies
        actionable = pending_tasks + blocked_tasks
        ready_tasks = [t for t in actionable if self._are_dependencies_met(t, tasks)]
        if actionable and not ready_tasks:
            return "blocked"

        # If there are actionable tasks (pending or blocked but some are ready)
        if actionable:
            return "queued"

        return mission["status"]

    def _are_dependencies_met(self, task: Dict, all_tasks: List[Dict]) -> bool:
        """Check if all dependencies of a task are completed."""
        deps = task.get("depends_on") or []
        if not deps:
            return True
        done_ids = {t["id"] for t in all_tasks if t["status"] in {"done", "completed"}}
        return all(dep in done_ids for dep in deps)
