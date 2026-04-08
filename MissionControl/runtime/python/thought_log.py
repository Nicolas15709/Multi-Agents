from dataclasses import dataclass
from typing import Dict, Optional

try:
    from .repository import MissionRepository
except ImportError:  # pragma: no cover - runtime script compatibility
    from repository import MissionRepository


@dataclass
class ThoughtLogService:
    mission_repository: MissionRepository

    def record(self, mission_id: str, step: str, summary: str, detail: Optional[Dict] = None) -> None:
        self.mission_repository.add_event(
            mission_id,
            event_type="thought_step",
            actor="planner",
            summary=summary,
            payload={
                "step": step,
                "detail": detail or {},
            },
        )

    def summary(self) -> dict:
        return {"status": "active"}
