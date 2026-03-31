"""Mission and Agent Loader System - Load configurations from files."""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone

from .models import Mission, AgentRecord, Task
from .repository import MissionRepository, AgentRepository
from .utils import new_id, utc_now


class LoaderError(Exception):
    """Base exception for loader errors."""
    pass


class ValidationError(LoaderError):
    """Raised when loaded data fails validation."""
    pass


class MissionLoader:
    """Loads missions from configuration files (JSON/YAML)."""

    @classmethod
    def load_from_file(cls, filepath: Union[str, Path]) -> List[Mission]:
        """Load missions from a file."""
        path = Path(filepath)
        if not path.exists():
            raise LoaderError(f"File not found: {filepath}")

        content = path.read_text(encoding="utf-8")
        data = cls._parse_content(content, path.suffix)

        missions = []
        for item in data.get("missions", []):
            mission = cls._validate_mission(item, path)
            missions.append(mission)

        return missions

    @classmethod
    def load_from_dict(cls, data: Dict[str, Any]) -> List[Mission]:
        """Load missions from a dictionary."""
        missions = []
        for item in data.get("missions", []):
            mission = cls._validate_mission(item, source="dict")
            missions.append(mission)
        return missions

    @staticmethod
    def _parse_content(content: str, suffix: str) -> Dict[str, Any]:
        """Parse file content based on extension."""
        suffix = suffix.lower()
        if suffix == ".json":
            return json.loads(content)
        elif suffix in [".yaml", ".yml"]:
            try:
                import yaml
                return yaml.safe_load(content)
            except ImportError:
                raise LoaderError("PyYAML is required for YAML files")
        else:
            raise LoaderError(f"Unsupported file format: {suffix}")

    @staticmethod
    def _validate_mission(data: Dict[str, Any], source: str = "file") -> Mission:
        """Validate and create a Mission from raw data."""
        required_fields = ["id", "title", "goal", "mode"]
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Mission missing required field '{field}' in {source}")

        # Validate enums
        priority = data.get("priority", "medium")
        if priority not in ["low", "medium", "high", "critical"]:
            raise ValidationError(f"Invalid priority '{priority}' for mission {data['id']}")

        status = data.get("status", "queued")
        if status not in ["queued", "running", "blocked", "needs_human", "completed"]:
            raise ValidationError(f"Invalid status '{status}' for mission {data['id']}")

        source_type = data.get("source", "manual")
        if source_type not in ["manual", "scheduled", "system"]:
            raise ValidationError(f"Invalid source '{source_type}' for mission {data['id']}")

        return Mission(
            id=data["id"],
            title=data["title"],
            goal=data["goal"],
            mode=data["mode"],
            priority=priority,
            status=status,
            source=source_type,
            schedule=data.get("schedule"),
            allow_24x7=data.get("allow_24x7", False),
        )


class AgentLoader:
    """Loads agents from configuration files."""

    @classmethod
    def load_from_file(cls, filepath: Union[str, Path]) -> List[AgentRecord]:
        """Load agents from a file."""
        path = Path(filepath)
        if not path.exists():
            raise LoaderError(f"File not found: {filepath}")

        content = path.read_text(encoding="utf-8")
        data = cls._parse_content(content, path.suffix)

        agents = []
        for item in data.get("agents", []):
            agent = cls._validate_agent(item, path)
            agents.append(agent)

        return agents

    @classmethod
    def load_from_dict(cls, data: Dict[str, Any]) -> List[AgentRecord]:
        """Load agents from a dictionary."""
        agents = []
        for item in data.get("agents", []):
            agent = cls._validate_agent(item, source="dict")
            agents.append(agent)
        return agents

    @staticmethod
    def _parse_content(content: str, suffix: str) -> Dict[str, Any]:
        """Parse file content based on extension."""
        suffix = suffix.lower()
        if suffix == ".json":
            return json.loads(content)
        elif suffix in [".yaml", ".yml"]:
            try:
                import yaml
                return yaml.safe_load(content)
            except ImportError:
                raise LoaderError("PyYAML is required for YAML files")
        else:
            raise LoaderError(f"Unsupported file format: {suffix}")

    @staticmethod
    def _validate_agent(data: Dict[str, Any], source: str = "file") -> AgentRecord:
        """Validate and create an AgentRecord from raw data."""
        required_fields = ["id", "display_name", "role"]
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Agent missing required field '{field}' in {source}")

        return AgentRecord(
            agent_id=data["id"],
            display_name=data["display_name"],
            role=data["role"],
            personality=data.get("personality"),
        )


class ConfigLoader:
    """Loads runtime configuration from environment and files."""

    @classmethod
    def load_runtime_config(cls, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Load runtime configuration."""
        import os

        env = env or os.environ
        base_dir = Path(__file__).resolve().parent

        config = {
            "db_path": env.get("MISSION_CONTROL_RUNTIME_DB", str(base_dir / ".." / ".." / "data" / "runtime.db")),
            "websocket_enabled": env.get("MISSION_CONTROL_WEBSOCKET", "true").lower() == "true",
            "websocket_host": env.get("MISSION_CONTROL_WEBSOCKET_HOST", "127.0.0.1"),
            "websocket_port": int(env.get("MISSION_CONTROL_WEBSOCKET_PORT", "8765")),
            "tick_interval_seconds": int(env.get("MISSION_CONTROL_TICK_INTERVAL_SECONDS", "5")),
            "telegram_notifications_enabled": env.get("MISSION_CONTROL_TELEGRAM_NOTIFICATIONS", "true").lower() == "true",
            "environment": env.get("MISSION_CONTROL_ENV", "development"),
            "agents_registry_path": env.get(
                "MISSION_CONTROL_AGENTS_REGISTRY",
                str(base_dir / "agents_registry.json")
            ),
            "templates_path": env.get(
                "MISSION_CONTROL_TEMPLATES_PATH",
                str(base_dir.parent.parent / "config" / "mission-templates.json")
            ),
        }

        # Load additional config files if specified
        config_file = env.get("MISSION_CONTROL_CONFIG_FILE")
        if config_file:
            path = Path(config_file)
            if path.exists():
                content = path.read_text(encoding="utf-8")
                data = json.loads(content)  # Only JSON for config overrides
                config.update(data)

        return config


class BulkLoader:
    """Orchestrates loading multiple entity types."""

    def __init__(
        self,
        mission_repository: Optional[MissionRepository] = None,
        agent_repository: Optional[AgentRepository] = None,
    ):
        self.mission_repository = mission_repository
        self.agent_repository = agent_repository
        self.load_results: Dict[str, Any] = {}

    def load_agents(self, filepath: Union[str, Path]) -> List[AgentRecord]:
        """Load and optionally persist agents."""
        agents = AgentLoader.load_from_file(filepath)
        self.load_results["agents_loaded"] = len(agents)

        if self.agent_repository:
            for agent in agents:
                self.agent_repository.upsert_agent(agent)
            self.load_results["agents_persisted"] = len(agents)

        return agents

    def load_missions(self, filepath: Union[str, Path], seed_workflow: bool = True) -> List[Mission]:
        """Load and optionally persist missions."""
        missions = MissionLoader.load_from_file(filepath)
        self.load_results["missions_loaded"] = len(missions)

        if self.mission_repository:
            for mission in missions:
                self.mission_repository.create_mission(mission)
            self.load_results["missions_persisted"] = len(missions)

        return missions

    def get_summary(self) -> Dict[str, Any]:
        """Get loading summary."""
        return self.load_results
