from dataclasses import dataclass
from typing import Dict, Optional

try:
    from .models import Mission
    from .notifications import NotificationService
    from .planner import Planner
    from .progress import ProgressNotifier
    from .repository import MissionControlRepository, MissionRepository
    from .scheduler import Scheduler
    from .state_machine import MissionStateMachine, StateValidationError
except ImportError:  # pragma: no cover - runtime script compatibility
    from models import Mission
    from notifications import NotificationService
    from planner import Planner
    from progress import ProgressNotifier
    from repository import MissionControlRepository, MissionRepository
    from scheduler import Scheduler
    from state_machine import MissionStateMachine, StateValidationError


@dataclass
class MissionService:
    planner: Planner
    mission_repository: MissionRepository
    scheduler: Scheduler
    notifications: NotificationService
    progress_notifier: ProgressNotifier
    state_updater: Optional[object] = None  # TransactionalStateUpdater
    hiring_service: Optional[object] = None
    auto_seed_hire_requests: bool = True
    mission_control_repository: Optional[MissionControlRepository] = None
    mission_control_defaults: Optional[Dict] = None

    def _transition_mission_status(self, mission_id: str, to_status: str, *, reason: str, actor: str) -> None:
        mission = self.mission_repository.get_mission(mission_id)
        if not mission:
            raise ValueError("mission not found")
        if mission.get("status") == to_status:
            return
        if self.state_updater:
            try:
                self.state_updater.begin_transaction()
                self.state_updater.transition_mission(
                    mission_id,
                    to_status,
                    reason=reason,
                    actor=actor,
                )
                self.state_updater.commit_transaction()
            except StateValidationError:
                self.state_updater.rollback_transaction()
                raise
        else:
            self.mission_repository.update_mission_status(mission_id, to_status)

    def submit_mission(self, title: str, goal: str, mode: str, priority: str = "medium", source: str = "manual", allow_24x7: bool = False, schedule: str = None) -> Dict:
        current = self.scheduler.highest_priority_mission()
        if current:
            conflict = self.scheduler.resolve_conflict(current["priority"], priority, source)
            if conflict["decision"] == "notify_user":
                self.notifications.enqueue(
                    kind="priority_conflict",
                    summary="A manual mission conflicts with an important mission already in progress.",
                    payload={
                        "current_mission_id": current["id"],
                        "incoming_priority": priority,
                        "reason": conflict["reason"],
                    },
                )
                self.progress_notifier.notify(
                    current["id"],
                    "priority_conflict",
                    "Hay conflicto entre una misión manual y otra misión importante en curso.",
                    {
                        "incoming_priority": priority,
                        "reason": conflict["reason"],
                    },
                )
        mission = self.planner.create_mission(
            title=title,
            goal=goal,
            mode=mode,
            priority=priority,
            source=source,
            allow_24x7=allow_24x7,
            schedule=schedule,
        )
        self.planner.seed_base_workflow(mission)
        control = None
        if self.mission_control_repository:
            control = self.mission_control_repository.ensure_control(
                mission.id,
                defaults=dict(self.mission_control_defaults or {}),
            )
            self.mission_repository.add_event(
                mission.id,
                "mission_budget_initialized",
                "system",
                "Mission autonomy budget initialized",
                {
                    "max_autonomous_steps": control.get("max_autonomous_steps"),
                    "max_estimated_tokens": control.get("max_estimated_tokens"),
                    "max_runtime_ticks": control.get("max_runtime_ticks"),
                    "max_dynamic_hires": control.get("max_dynamic_hires"),
                },
            )
        # Use state_updater to transition mission from initial creation state to queued if needed
        if self.state_updater:
            try:
                self.state_updater.begin_transaction()
                self.state_updater.transition_mission(
                    mission.id,
                    "queued",
                    reason="mission_submitted",
                    actor=source
                )
                self.state_updater.commit_transaction()
            except StateValidationError:
                # If transition not needed (already queued), just commit without transition
                self.state_updater.rollback_transaction()
        hire_seed_result = {
            "created": 0,
            "duplicates": 0,
            "request_ids": [],
            "status": "skipped",
        }
        if self.auto_seed_hire_requests and self.hiring_service and hasattr(self.hiring_service, "seed_suggested_requests_for_mission"):
            try:
                hire_seed_result = dict(
                    self.hiring_service.seed_suggested_requests_for_mission(
                        mission.id,
                        requested_by_agent_id="agent-0",
                        reports_to="agent-0",
                        force_pending=True,
                    )
                )
                hire_seed_result["status"] = "seeded" if hire_seed_result.get("created") else "unchanged"
                if hire_seed_result.get("created"):
                    self.mission_repository.add_event(
                        mission.id,
                        "subagent_requests_seeded",
                        "system",
                        f"Auto-proposed {hire_seed_result['created']} specialist requests.",
                        {
                            "request_ids": hire_seed_result.get("request_ids", []),
                            "duplicates": hire_seed_result.get("duplicates", 0),
                        },
                    )
            except Exception as error:  # pragma: no cover - defensive runtime guard
                hire_seed_result = {
                    "created": 0,
                    "duplicates": 0,
                    "request_ids": [],
                    "status": "failed",
                    "error": str(error),
                }
                self.mission_repository.add_event(
                    mission.id,
                    "subagent_request_seeding_failed",
                    "system",
                    "Failed to auto-propose specialist requests.",
                    {"error": str(error)},
                )
        self.notifications.enqueue(
            kind="mission_submitted",
            summary=f"Mission queued: {title}",
            payload={
                "mission_id": mission.id,
                "mode": mode,
                "hire_requests_seeded": hire_seed_result.get("created", 0),
            },
        )
        self.progress_notifier.notify(
            mission.id,
            "mission_created",
            f"Nueva misión creada: {title}",
            {"mode": mode, "priority": priority},
        )
        return {
            "mission_id": mission.id,
            "status": mission.status,
            "hire_requests_seeded": hire_seed_result.get("created", 0),
            "hire_request_ids": hire_seed_result.get("request_ids", []),
            "mission_control": control,
        }

    def pause_mission(self, mission_id: str, *, actor: str = "operator") -> Dict:
        mission = self.mission_repository.get_mission(mission_id)
        if not mission:
            raise ValueError("mission not found")
        if mission.get("status") == "completed":
            raise ValueError("completed mission cannot be paused")
        self._transition_mission_status(
            mission_id,
            "queued",
            reason="manual_pause",
            actor=actor,
        )
        control = None
        if self.mission_control_repository:
            control = self.mission_control_repository.update_status(
                mission_id,
                status="paused",
                notes="manual_pause",
            )
        self.mission_repository.add_event(
            mission_id,
            "mission_paused_manual",
            actor,
            "Mission paused manually",
            {"mission_id": mission_id},
        )
        return {
            "ok": True,
            "mission_id": mission_id,
            "status": "queued",
            "mission_control": control,
        }

    def resume_mission(self, mission_id: str, *, actor: str = "operator") -> Dict:
        mission = self.mission_repository.get_mission(mission_id)
        if not mission:
            raise ValueError("mission not found")
        if mission.get("status") == "completed":
            raise ValueError("completed mission cannot be resumed")
        self._transition_mission_status(
            mission_id,
            "queued",
            reason="manual_resume",
            actor=actor,
        )
        control = None
        if self.mission_control_repository:
            control = self.mission_control_repository.update_status(
                mission_id,
                status="active",
                notes=None,
            )
        self.mission_repository.add_event(
            mission_id,
            "mission_resumed_manual",
            actor,
            "Mission resumed manually",
            {"mission_id": mission_id},
        )
        return {
            "ok": True,
            "mission_id": mission_id,
            "status": "queued",
            "mission_control": control,
        }
