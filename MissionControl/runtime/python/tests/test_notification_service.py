"""Tests for NotificationService."""

from unittest.mock import MagicMock, patch

import pytest

from runtime.python.notifications import NotificationService
from runtime.python.models import NotificationRecord


@pytest.fixture
def mock_repository():
    """Create a mock notification repository."""
    return MagicMock()


@pytest.fixture
def notification_service(mock_config, mock_repository):
    """Create a NotificationService instance."""
    return NotificationService(config=mock_config, repository=mock_repository)


def test_enqueue_creates_notification(notification_service, mock_repository):
    """Test that enqueue creates a notification record."""
    notification_service.enqueue(
        kind="mission_complete",
        summary="Mission completed successfully",
        payload={"mission_id": "test-123"},
        channel="telegram",
    )

    mock_repository.create_notification.assert_called_once()
    call_args = mock_repository.create_notification.call_args[0][0]

    assert isinstance(call_args, NotificationRecord)
    assert call_args.channel == "telegram"
    assert call_args.kind == "mission_complete"
    assert call_args.status == "queued"
    assert call_args.summary == "Mission completed successfully"
    assert call_args.payload == {"mission_id": "test-123"}


def test_enqueue_default_channel(notification_service, mock_repository):
    """Test that enqueue uses 'telegram' as default channel."""
    notification_service.enqueue(
        kind="alert",
        summary="Test alert",
    )

    call_args = mock_repository.create_notification.call_args[0][0]
    assert call_args.channel == "telegram"


def test_enqueue_empty_payload(notification_service, mock_repository):
    """Test that enqueue handles empty payload."""
    notification_service.enqueue(
        kind="heartbeat",
        summary="System alive",
    )

    call_args = mock_repository.create_notification.call_args[0][0]
    assert call_args.payload == {}


def test_summary_returns_dict(notification_service):
    """Test that summary returns expected structure."""
    summary = notification_service.summary()
    assert isinstance(summary, dict)
    assert summary["channel"] == "telegram"
    assert "usage" in summary
    assert "queued" in summary
