"""Tests for RuntimeConfig."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.python.config import RuntimeConfig


def test_runtime_config_defaults():
    """Test default configuration values."""
    with patch.dict(os.environ, {}, clear=True):
        config = RuntimeConfig.from_env()

        assert config.websocket_enabled is True
        assert config.websocket_host == "127.0.0.1"
        assert config.websocket_port == 8765
        assert config.tick_interval_seconds == 5
        assert config.telegram_notifications_enabled is True
        assert config.environment == "development"


def test_runtime_config_from_env():
    """Test configuration from environment variables."""
    with patch.dict(
        os.environ,
        {
            "MISSION_CONTROL_RUNTIME_DB": "/custom/path/db.sqlite",
            "MISSION_CONTROL_WEBSOCKET": "false",
            "MISSION_CONTROL_WEBSOCKET_HOST": "0.0.0.0",
            "MISSION_CONTROL_WEBSOCKET_PORT": "9999",
            "MISSION_CONTROL_TICK_INTERVAL_SECONDS": "10",
            "MISSION_CONTROL_TELEGRAM_NOTIFICATIONS": "false",
            "MISSION_CONTROL_ENV": "production",
        },
    ):
        config = RuntimeConfig.from_env()

        assert config.db_path == "/custom/path/db.sqlite"
        assert config.websocket_enabled is False
        assert config.websocket_host == "0.0.0.0"
        assert config.websocket_port == 9999
        assert config.tick_interval_seconds == 10
        assert config.telegram_notifications_enabled is False
        assert config.environment == "production"


def test_runtime_config_paths():
    """Test that config paths are resolved correctly."""
    config = RuntimeConfig.from_env()

    # These should be absolute paths
    assert Path(config.agents_registry_path).is_absolute() or Path(
        config.agents_registry_path
    ).exists()
    assert Path(config.templates_path).is_absolute() or Path(
        config.templates_path
    ).exists()
    assert Path(config.specialist_templates_root).is_absolute() or Path(
        config.specialist_templates_root
    ).exists()
