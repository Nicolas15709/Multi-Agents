from dataclasses import dataclass
import os
from pathlib import Path


@dataclass
class RuntimeConfig:
    db_path: str
    websocket_enabled: bool
    telegram_notifications_enabled: bool
    environment: str
    agents_registry_path: str
    templates_path: str

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        base_dir = Path(__file__).resolve().parent
        return cls(
            db_path=os.getenv("MISSION_CONTROL_RUNTIME_DB", str(base_dir / ".." / ".." / "data" / "runtime.db")),
            websocket_enabled=os.getenv("MISSION_CONTROL_WEBSOCKET", "true").lower() == "true",
            telegram_notifications_enabled=os.getenv("MISSION_CONTROL_TELEGRAM_NOTIFICATIONS", "true").lower() == "true",
            environment=os.getenv("MISSION_CONTROL_ENV", "development"),
            agents_registry_path=os.getenv("MISSION_CONTROL_AGENTS_REGISTRY", str(base_dir / "agents_registry.json")),
            templates_path=os.getenv("MISSION_CONTROL_TEMPLATES_PATH", str(base_dir.parent.parent / "config" / "mission-templates.json")),
        )
