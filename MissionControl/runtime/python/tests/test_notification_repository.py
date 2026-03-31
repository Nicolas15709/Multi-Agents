"""Tests for NotificationRepository."""

import uuid
from datetime import datetime

import pytest

from runtime.python.models import NotificationRecord
from runtime.python.repository import NotificationRepository
from runtime.python.utils import utc_now


def create_test_notification(
    channel="telegram",
    kind="test",
    status="queued",
    summary="Test notification",
    payload=None,
):
    """Helper to create a test notification."""
    return NotificationRecord(
        channel=channel,
        kind=kind,
        status=status,
        summary=summary,
        payload=payload or {},
    )


def test_create_notification(notification_repository):
    """Test creating a notification."""
    notification = create_test_notification()
    notification_repository.create_notification(notification)

    notifications = notification_repository.recent_notifications(limit=1)
    assert len(notifications) == 1
    assert notifications[0]["channel"] == "telegram"
    assert notifications[0]["kind"] == "test"
    assert notifications[0]["status"] == "queued"
    assert notifications[0]["summary"] == "Test notification"


def test_recent_notifications_ordered(notification_repository):
    """Test that recent notifications are ordered correctly."""
    now = utc_now()
    notif1 = create_test_notification(summary="First")
    notif2 = create_test_notification(summary="Second")
    notif3 = create_test_notification(summary="Third")

    notification_repository.create_notification(notif3)
    notification_repository.create_notification(notif2)
    notification_repository.create_notification(notif1)

    notifications = notification_repository.recent_notifications(limit=3)
    summaries = [n["summary"] for n in notifications]
    # Should be in reverse chronological order (newest first due to id DESC)
    # Insertion order: Third (id 1), Second (id 2), First (id 3) -> Newest is First (id 3)
    assert summaries == ["First", "Second", "Third"]


def test_notification_payload_deserialization(notification_repository):
    """Test that payload is properly deserialized."""
    notification = create_test_notification(
        payload={"mission_id": str(uuid.uuid4()), "count": 42}
    )
    notification_repository.create_notification(notification)

    notifications = notification_repository.recent_notifications(limit=1)
    retrieved = notifications[0]
    assert isinstance(retrieved["payload"], dict)
    assert "mission_id" in retrieved["payload"]
    assert retrieved["payload"]["count"] == 42


def test_recent_notifications_limit(notification_repository):
    """Test limiting the number of notifications returned."""
    for i in range(10):
        notif = create_test_notification(summary=f"Notification {i}")
        notification_repository.create_notification(notif)

    notifications = notification_repository.recent_notifications(limit=5)
    assert len(notifications) == 5
