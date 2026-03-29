from dataclasses import dataclass
from typing import Dict

from models import Mission
from notifications import NotificationService
from planner import Planner
from progress import ProgressNotifier
from repository import MissionRepository
from scheduler import Scheduler


@dataclass
class MissionService:
    planner: Planner
    mission_repository: MissionRepository
    scheduler: Scheduler
    notifications: NotificationService
    progress_notifier: ProgressNotifier

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
        self.notifications.enqueue(
            kind="mission_submitted",
            summary=f"Mission queued: {title}",
            payload={"mission_id": mission.id, "mode": mode},
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
        }
