"""Pytest configuration and fixtures for Virtual Agency tests."""

import os
import sys
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Add MissionControl root to path for imports
MISSION_CONTROL_ROOT = Path(__file__).resolve().parent.parent.parent
if str(MISSION_CONTROL_ROOT) not in sys.path:
    sys.path.insert(0, str(MISSION_CONTROL_ROOT))

import pytest

from runtime.python.db import Database
from runtime.python.repository import (
    AgentHireRequestRepository,
    AgentRepository,
    IntakeRequestRepository,
    MissionControlRepository,
    MissionRepository,
    NotificationRepository,
    PolicyRepository,
    TaskRepository,
)
from runtime.python.config import RuntimeConfig


@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def database(temp_db_path):
    """Create a Database instance with initialized schema."""
    db = Database(temp_db_path)
    db.init()
    yield db
    db.close()


@pytest.fixture
def mission_repository(database):
    """Create a MissionRepository instance."""
    return MissionRepository(database)


@pytest.fixture
def task_repository(database):
    """Create a TaskRepository instance."""
    return TaskRepository(database)


@pytest.fixture
def agent_repository(database):
    """Create an AgentRepository instance."""
    return AgentRepository(database)


@pytest.fixture
def policy_repository(database):
    """Create a PolicyRepository instance."""
    return PolicyRepository(database)


@pytest.fixture
def notification_repository(database):
    """Create a NotificationRepository instance."""
    return NotificationRepository(database)


@pytest.fixture
def intake_request_repository(database):
    """Create an IntakeRequestRepository instance."""
    return IntakeRequestRepository(database)


@pytest.fixture
def agent_hire_request_repository(database):
    """Create an AgentHireRequestRepository instance."""
    return AgentHireRequestRepository(database)


@pytest.fixture
def mission_control_repository(database):
    """Create a MissionControlRepository instance."""
    return MissionControlRepository(database)


@pytest.fixture
def mock_config():
    """Create a mock RuntimeConfig."""
    config = MagicMock(spec=RuntimeConfig)
    config.db_path = ":memory:"
    config.websocket_enabled = False
    config.websocket_host = "127.0.0.1"
    config.websocket_port = 8765
    config.api_enabled = False
    config.api_host = "127.0.0.1"
    config.api_port = 8787
    config.api_cors_origin = "*"
    config.api_auth_token = ""
    config.hire_approvals_enabled = False
    config.auto_propose_hires_enabled = True
    config.max_autonomous_steps = 18
    config.max_estimated_tokens = 16000
    config.max_runtime_ticks = 64
    config.max_dynamic_hires = 3
    config.action_budgets = {"outreach": 2, "publish": 1, "legal_release": 1, "financial_commitment": 1}
    config.tick_interval_seconds = 1
    config.telegram_notifications_enabled = True
    config.environment = "test"
    base_dir = Path(__file__).resolve().parent.parent
    config.agents_registry_path = str(base_dir / "agents_registry.json")
    config.templates_path = str(
        base_dir.parent.parent / "config" / "mission-templates.json"
    )
    config.specialist_templates_root = str(
        base_dir.parent.parent.parent / "references" / "agency-agents"
    )
    return config

