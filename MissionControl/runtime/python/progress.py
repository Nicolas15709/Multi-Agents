from dataclasses import dataclass
from typing import Dict, Optional

try:
    from .notifications import NotificationService
    from .repository import MissionRepository
except ImportError:  # pragma: no cover - runtime script compatibility
    from notifications import NotificationService
    from repository import MissionRepository


@dataclass
class ProgressNotifier:
    mission_repository: MissionRepository
    notifications: NotificationService
    mode: str = "phase_updates"

    def notify(self, mission_id: str, kind: str, summary: str, payload: Optional[Dict] = None) -> None:
        if self.mode == "off":
            return
        important_kinds = {
            "mission_created",
            "task_started",
            "task_completed",
            "handoff",
            "blocked",
            "priority_conflict",
            "mission_completed",
        }
        if self.mode == "important_only" and kind not in {"blocked", "priority_conflict", "mission_completed"}:
            return
        if self.mode == "phase_updates" and kind not in important_kinds:
            return

        self.notifications.enqueue(
            kind="progress_update",
            summary=summary,
            payload={
                "mission_id": mission_id,
                "event_kind": kind,
                **(payload or {}),
            },
        )

    def summary(self) -> Dict:
        return {
            "mode": self.mode,
            "channel": "telegram",
        }
