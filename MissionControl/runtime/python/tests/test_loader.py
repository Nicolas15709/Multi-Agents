"""Tests for the loader module."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from runtime.python.loader import (
    MissionLoader,
    AgentLoader,
    ConfigLoader,
    BulkLoader,
    ValidationError,
    LoaderError,
)
from runtime.python.models import Mission, AgentRecord
from runtime.python.repository import MissionRepository, AgentRepository
from runtime.python.db import Database


class TestMissionLoader:
    """Tests for MissionLoader."""

    def test_load_from_json(self, tmp_path):
        """Test loading missions from JSON file."""
        data = {
            "missions": [
                {
                    "id": "mission-1",
                    "title": "Test Mission",
                    "goal": "Test goal",
                    "mode": "test_mode",
                    "priority": "high",
                    "status": "queued",
                    "source": "manual",
                    "allow_24x7": True,
                },
                {
                    "id": "mission-2",
                    "title": "Second Mission",
                    "goal": "Second goal",
                    "mode": "another_mode",
                },
            ]
        }
        filepath = tmp_path / "missions.json"
        filepath.write_text(json.dumps(data))

        missions = MissionLoader.load_from_file(filepath)

        assert len(missions) == 2
        assert missions[0].id == "mission-1"
        assert missions[0].title == "Test Mission"
        assert missions[0].priority == "high"
        assert missions[0].allow_24x7 is True
        assert missions[1].id == "mission-2"
        assert missions[1].priority == "medium"  # default

    def test_load_from_yaml(self, tmp_path):
        """Test loading missions from YAML file."""
        yaml_content = """
missions:
  - id: mission-yaml-1
    title: YAML Mission
    goal: YAML goal
    mode: test_mode
    priority: critical
    status: running
    source: scheduled
  - id: mission-yaml-2
    title: Second YAML
    goal: Another goal
    mode: dev_mode
"""
        filepath = tmp_path / "missions.yaml"
        filepath.write_text(yaml_content)

        missions = MissionLoader.load_from_file(filepath)

        assert len(missions) == 2
        assert missions[0].id == "mission-yaml-1"
        assert missions[0].priority == "critical"
        assert missions[1].id == "mission-yaml-2"

    def test_validate_required_fields(self):
        """Test validation of required fields."""
        invalid_data = {"missions": [{"title": "Missing id and goal"}]}
        with pytest.raises(ValidationError, match="missing required field"):
            MissionLoader.load_from_dict(invalid_data)

    def test_validate_priority(self):
        """Test validation of priority enum."""
        data = {"missions": [{"id": "m1", "title": "Test", "goal": "Goal", "mode": "test", "priority": "invalid"}]}
        with pytest.raises(ValidationError, match="Invalid priority"):
            MissionLoader.load_from_dict(data)

    def test_validate_status(self):
        """Test validation of status enum."""
        data = {"missions": [{"id": "m1", "title": "Test", "goal": "Goal", "mode": "test", "status": "invalid_status"}]}
        with pytest.raises(ValidationError, match="Invalid status"):
            MissionLoader.load_from_dict(data)

    def test_validate_source(self):
        """Test validation of source enum."""
        data = {"missions": [{"id": "m1", "title": "Test", "goal": "Goal", "mode": "test", "source": "invalid_source"}]}
        with pytest.raises(ValidationError, match="Invalid source"):
            MissionLoader.load_from_dict(data)

    def test_load_from_dict(self):
        """Test loading from dictionary."""
        data = {
            "missions": [
                {
                    "id": "m1",
                    "title": "Dict Mission",
                    "goal": "Dict goal",
                    "mode": "dict_mode",
                }
            ]
        }
        missions = MissionLoader.load_from_dict(data)
        assert len(missions) == 1
        assert missions[0].id == "m1"

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file raises error."""
        with pytest.raises(LoaderError, match="File not found"):
            MissionLoader.load_from_file("/nonexistent/file.json")

    def test_unsupported_format(self, tmp_path):
        """Test unsupported file format raises error."""
        filepath = tmp_path / "missions.txt"
        filepath.write_text("some content")
        with pytest.raises(LoaderError, match="Unsupported file format"):
            MissionLoader.load_from_file(filepath)


class TestAgentLoader:
    """Tests for AgentLoader."""

    def test_load_from_json(self, tmp_path):
        """Test loading agents from JSON file."""
        data = {
            "agents": [
                {
                    "id": "agent-0",
                    "display_name": "Supervisor",
                    "role": "director",
                    "personality": "Analytical and focused.",
                },
                {
                    "id": "agent-1",
                    "display_name": "Researcher",
                    "role": "finder",
                },
            ]
        }
        filepath = tmp_path / "agents.json"
        filepath.write_text(json.dumps(data))

        agents = AgentLoader.load_from_file(filepath)

        assert len(agents) == 2
        assert agents[0].agent_id == "agent-0"
        assert agents[0].display_name == "Supervisor"
        assert agents[0].personality == "Analytical and focused."
        assert agents[1].agent_id == "agent-1"
        assert agents[1].personality is None  # optional

    def test_load_from_yaml(self, tmp_path):
        """Test loading agents from YAML file."""
        yaml_content = """
agents:
  - id: agent-test
    display_name: Test Agent
    role: tester
"""
        filepath = tmp_path / "agents.yaml"
        filepath.write_text(yaml_content)

        agents = AgentLoader.load_from_file(filepath)
        assert len(agents) == 1
        assert agents[0].agent_id == "agent-test"

    def test_validate_required_fields(self):
        """Test validation of required fields."""
        invalid_data = {"agents": [{"display_name": "Missing id and role"}]}
        with pytest.raises(ValidationError, match="missing required field"):
            AgentLoader.load_from_dict(invalid_data)

    def test_load_from_dict(self):
        """Test loading from dictionary."""
        data = {
            "agents": [
                {
                    "id": "agent-custom",
                    "display_name": "Custom Agent",
                    "role": "custom_role",
                }
            ]
        }
        agents = AgentLoader.load_from_dict(data)
        assert len(agents) == 1
        assert agents[0].agent_id == "agent-custom"


class TestBulkLoader:
    """Tests for BulkLoader."""

    def test_load_agents_with_persistence(self, tmp_path, database):
        """Test loading and persisting agents."""
        data = {
            "agents": [
                {"id": "agent-bulk-1", "display_name": "Bulk Agent 1", "role": "role1"},
                {"id": "agent-bulk-2", "display_name": "Bulk Agent 2", "role": "role2"},
            ]
        }
        filepath = tmp_path / "agents.json"
        filepath.write_text(json.dumps(data))

        agent_repo = AgentRepository(database)
        loader = BulkLoader(agent_repository=agent_repo)
        agents = loader.load_agents(filepath)

        assert len(agents) == 2
        assert loader.load_results["agents_loaded"] == 2
        assert loader.load_results["agents_persisted"] == 2

        # Verify persisted
        stored_agents = agent_repo.list_agents()
        assert len(stored_agents) == 2
        agent_ids = {a["agent_id"] for a in stored_agents}
        assert agent_ids == {"agent-bulk-1", "agent-bulk-2"}

    def test_load_missions_without_persistence(self, tmp_path):
        """Test loading missions without repository."""
        data = {
            "missions": [
                {"id": "m1", "title": "Test", "goal": "Goal", "mode": "test"},
            ]
        }
        filepath = tmp_path / "missions.json"
        filepath.write_text(json.dumps(data))

        loader = BulkLoader()
        missions = loader.load_missions(filepath)

        assert len(missions) == 1
        assert loader.load_results["missions_loaded"] == 1
        assert "missions_persisted" not in loader.load_results

    def test_get_summary(self, tmp_path, database):
        """Test getting load summary."""
        data = {
            "agents": [{"id": "a1", "display_name": "A1", "role": "r1"}],
            "missions": [{"id": "m1", "title": "M1", "goal": "G1", "mode": "mode1"}],
        }
        filepath = tmp_path / "data.json"
        filepath.write_text(json.dumps(data))

        agent_repo = AgentRepository(database)
        mission_repo = MissionRepository(database)
        loader = BulkLoader(
            agent_repository=agent_repo,
            mission_repository=mission_repo,
        )
        # Load agents
        loader.load_agents(filepath)
        # Load missions
        loader.load_missions(filepath)

        summary = loader.get_summary()
        assert summary["agents_loaded"] == 1
        assert summary["agents_persisted"] == 1
        assert summary["missions_loaded"] == 1
        assert summary["missions_persisted"] == 1


class TestConfigLoader:
    """Tests for ConfigLoader."""

    def test_load_default_config(self, monkeypatch):
        """Test loading default configuration from environment."""
        monkeypatch.setenv("MISSION_CONTROL_WEBSOCKET", "false")
        monkeypatch.setenv("MISSION_CONTROL_TICK_INTERVAL_SECONDS", "10")
        monkeypatch.setenv("MISSION_CONTROL_ENV", "production")

        config = ConfigLoader.load_runtime_config()

        assert config["websocket_enabled"] is False
        assert config["tick_interval_seconds"] == 10
        assert config["environment"] == "production"
        # Defaults should still be present
        assert "db_path" in config
        assert "websocket_host" in config
        assert "websocket_port" in config

    def test_load_config_with_override_file(self, tmp_path, monkeypatch):
        """Test loading config with override file."""
        override_data = {
            "websocket_port": 9999,
            "tick_interval_seconds": 15,
            "custom_setting": "custom_value",
        }
        override_file = tmp_path / "override.json"
        override_file.write_text(json.dumps(override_data))
        monkeypatch.setenv("MISSION_CONTROL_CONFIG_FILE", str(override_file))

        config = ConfigLoader.load_runtime_config()

        assert config["websocket_port"] == 9999
        assert config["tick_interval_seconds"] == 15
        assert config["custom_setting"] == "custom_value"
