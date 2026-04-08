from dataclasses import dataclass
from typing import Dict, List

try:
    from .api_snapshot import RuntimeSnapshotAPI
    from .mission_lifecycle import MissionLifecycleService
    from .startup_recovery import StartupRecoveryService
except ImportError:  # pragma: no cover - runtime script compatibility
    from api_snapshot import RuntimeSnapshotAPI
    from mission_lifecycle import MissionLifecycleService
    from startup_recovery import StartupRecoveryService


@dataclass
class StatusReportService:
    snapshot_api: RuntimeSnapshotAPI
    lifecycle: MissionLifecycleService
    recovery: StartupRecoveryService

    def build(self) -> Dict:
        snapshot = self.snapshot_api.snapshot()
        progress = snapshot.get("progress", {})
        mission = progress.get("mission") or snapshot.get("activeMission")
        counts = progress.get("progress", {})
        mission_summary = snapshot.get("missionSummary") or {}
        mission_control = snapshot.get("activeMissionControl") or {}
        events = snapshot.get("stream", {}).get("events", [])
        notifications = snapshot.get("stream", {}).get("notifications", [])
        recovery_summary = self.recovery.inspect()
        scheduler_meta = snapshot.get("scheduler", {})
        active_agents = [agent for agent in snapshot.get("agents", []) if agent.get("state") and agent.get("state") != "idle"]

        return {
            "mission": mission,
            "progress": counts,
            "mission_summary": mission_summary,
            "mission_control": mission_control,
            "meta": snapshot.get("meta", {}),
            "runtime": {
                "focus_mission_id": snapshot.get("activeMission", {}).get("id") if snapshot.get("activeMission") else None,
                "focus_mission_status": snapshot.get("activeMission", {}).get("status") if snapshot.get("activeMission") else None,
                "active_agents": [
                    {
                        "agent_id": agent.get("agent_id"),
                        "state": agent.get("state"),
                        "mission_id": agent.get("active_mission_id"),
                        "task_id": agent.get("current_task_id"),
                    }
                    for agent in active_agents
                ],
                "queued_missions": scheduler_meta.get("queued_missions", []),
                "blocked_missions": scheduler_meta.get("blocked_missions", []),
                "recovery": recovery_summary,
            },
            "recent_events": self._tail(events, 8),
            "recent_notifications": self._tail(notifications, 8),
            "health": {
                "has_mission": mission is not None,
                "has_active_tasks": counts.get("running", 0) > 0 or counts.get("pending", 0) > 0,
                "blocked_tasks": counts.get("blocked", 0),
                "percent_complete": counts.get("percent", 0),
                "queued_mission_count": len(scheduler_meta.get("queued_missions", [])),
                "blocked_mission_count": len(scheduler_meta.get("blocked_missions", [])),
                "recovery_required": recovery_summary.get("status") == "needs_recovery",
                "budget_status": mission_control.get("status"),
            },
        }

    @staticmethod
    def _tail(items: List[Dict], limit: int) -> List[Dict]:
        return items[-limit:] if len(items) > limit else items
