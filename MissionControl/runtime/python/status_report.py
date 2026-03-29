from dataclasses import dataclass
from typing import Dict, List

from api_snapshot import RuntimeSnapshotAPI
from mission_lifecycle import MissionLifecycleService


@dataclass
class StatusReportService:
    snapshot_api: RuntimeSnapshotAPI
    lifecycle: MissionLifecycleService

    def build(self) -> Dict:
        snapshot = self.snapshot_api.snapshot()
        progress = snapshot.get("progress", {})
        mission = progress.get("mission") or snapshot.get("activeMission")
        counts = progress.get("progress", {})
        mission_summary = snapshot.get("missionSummary") or {}
        events = snapshot.get("stream", {}).get("events", [])
        notifications = snapshot.get("stream", {}).get("notifications", [])

        return {
            "mission": mission,
            "progress": counts,
            "mission_summary": mission_summary,
            "meta": snapshot.get("meta", {}),
            "recent_events": self._tail(events, 8),
            "recent_notifications": self._tail(notifications, 8),
            "health": {
                "has_mission": mission is not None,
                "has_active_tasks": counts.get("running", 0) > 0 or counts.get("pending", 0) > 0,
                "blocked_tasks": counts.get("blocked", 0),
                "percent_complete": counts.get("percent", 0),
            },
        }

    @staticmethod
    def _tail(items: List[Dict], limit: int) -> List[Dict]:
        return items[-limit:] if len(items) > limit else items
