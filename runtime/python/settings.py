from dataclasses import dataclass
import os


@dataclass
class ProgressSettings:
    telegram_progress_mode: str = "phase_updates"

    @classmethod
    def from_env(cls) -> "ProgressSettings":
        return cls(
            telegram_progress_mode=os.getenv("MISSION_CONTROL_TELEGRAM_PROGRESS_MODE", "phase_updates"),
        )
