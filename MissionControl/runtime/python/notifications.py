from dataclasses import dataclass
from typing import Dict

from .models import NotificationRecord
from .repository import NotificationRepository


@dataclass
class NotificationService:
    config: object
    repository: NotificationRepository

    def enqueue(self, kind: str, summary: str, payload: Dict = None, channel: str = "telegram") -> None:
        self.repository.create_notification(
            NotificationRecord(
                channel=channel,
                kind=kind,
                status="queued",
                summary=summary,
                payload=payload or {},
            )
        )

    def summary(self) -> dict:
        return {
            "channel": "telegram",
            "usage": "alerts_and_decisions",
            "queued": len(self.repository.recent_notifications(limit=50)),
        }
