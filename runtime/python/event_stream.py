from typing import Dict, List

from repository import MissionRepository, NotificationRepository


class EventStreamService:
    def __init__(self, mission_repository: MissionRepository, notification_repository: NotificationRepository):
        self.mission_repository = mission_repository
        self.notification_repository = notification_repository

    def snapshot(self) -> Dict:
        return {
            "events": self.mission_repository.recent_events(limit=15),
            "notifications": self.notification_repository.recent_notifications(limit=10),
        }

    def summary(self) -> Dict:
        data = self.snapshot()
        return {
            "events": len(data["events"]),
            "notifications": len(data["notifications"]),
        }
