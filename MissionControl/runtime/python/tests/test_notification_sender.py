"""Tests for NotificationDeliveryService."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from runtime.python.models import NotificationRecord
from runtime.python.notification_sender import NotificationDeliveryService, NotificationProcessor


@pytest.fixture
def delivery_service():
    """Create a delivery service with test credentials."""
    return NotificationDeliveryService(
        telegram_bot_token="test-bot-token",
        telegram_chat_id="test-chat-id",
        slack_webhook_url="https://hooks.slack.com/test",
    )


def test_send_telegram_success(delivery_service):
    """Test successful Telegram message send."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "ok"

    with patch.object(requests, "post", return_value=mock_response) as mock_post:
        success = delivery_service.send_telegram(
            summary="Test alert", payload={"key": "value"}
        )

    assert success is True

    # Verify the request was made correctly
    mock_post.assert_called_once()
    url = mock_post.call_args[0][0]
    # Telegram API: /bot<token>/sendMessage
    assert url == "https://api.telegram.org/bottest-bot-token/sendMessage"

    data = mock_post.call_args[1]["data"]
    assert data["chat_id"] == "test-chat-id"
    assert "<b>Test alert</b>" in data["text"]
    assert '"key": "value"' in data["text"]
    assert data["parse_mode"] == "HTML"
    assert data["disable_notification"] is False  # default kind is "notification"


def test_send_telegram_http_error(delivery_service):
    """Test Telegram API returns an error."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = '{"error": "Forbidden"}'

    with patch.object(requests, "post", return_value=mock_response):
        success = delivery_service.send_telegram(summary="Test")

    assert success is False


def test_send_telegram_request_exception(delivery_service):
    """Test Telegram request raises exception."""
    with patch.object(requests, "post", side_effect=requests.RequestException("Network error")):
        success = delivery_service.send_telegram(summary="Test")

    assert success is False


def test_send_telegram_not_configured():
    """Test Telegram send without configuration."""
    service = NotificationDeliveryService()  # No credentials
    success = service.send_telegram(summary="Test")
    assert success is False


def test_send_telegram_heartbeat_kind(delivery_service):
    """Test that heartbeat notifications are silent."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(requests, "post", return_value=mock_response) as mock_post:
        success = delivery_service.send_telegram(summary="Heartbeat", kind="heartbeat")
        assert success is True
        data = mock_post.call_args[1]["data"]
        assert data["disable_notification"] is True


def test_send_slack_success(delivery_service):
    """Test successful Slack webhook."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "ok"

    with patch.object(requests, "post", return_value=mock_response) as mock_post:
        success = delivery_service.send_slack(
            summary="Test alert", payload={"key": "value"}
        )

    assert success is True

    # Verify Slack payload format
    mock_post.assert_called_once()
    url = mock_post.call_args[0][0]
    assert url == "https://hooks.slack.com/test"

    json_data = mock_post.call_args[1]["json"]
    assert len(json_data["attachments"]) == 1
    attachment = json_data["attachments"][0]
    assert "Test alert" in attachment["text"]
    assert '"key": "value"' in attachment["text"]
    assert attachment["color"] == "#36a64f"  # green for normal


def test_send_slack_error(delivery_service):
    """Test Slack webhook returns an error."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch.object(requests, "post", return_value=mock_response):
        success = delivery_service.send_slack(summary="Test")

    assert success is False


def test_send_slack_request_exception(delivery_service):
    """Test Slack request raises exception."""
    with patch.object(requests, "post", side_effect=requests.RequestException("Network error")):
        success = delivery_service.send_slack(summary="Test")

    assert success is False


def test_send_slack_not_configured():
    """Test Slack send without webhook URL."""
    service = NotificationDeliveryService()
    success = service.send_slack(summary="Test")
    assert success is False


def test_send_slack_error_kind(delivery_service):
    """Test that error kind changes Slack attachment color."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(requests, "post", return_value=mock_response) as mock_post:
        success = delivery_service.send_slack(summary="Error", kind="error")
        assert success is True
        json_data = mock_post.call_args[1]["json"]
        assert json_data["attachments"][0]["color"] == "#ff0000"  # red for errors


def test_send_unknown_channel(delivery_service):
    """Test sending to unknown channel returns False."""
    success = delivery_service.send(channel="unknown", summary="Test")
    assert success is False


def test_is_configured(delivery_service):
    """Test channel configuration checks."""
    assert delivery_service.is_configured("telegram") is True
    assert delivery_service.is_configured("slack") is True

    service_no_creds = NotificationDeliveryService()
    assert service_no_creds.is_configured("telegram") is False
    assert service_no_creds.is_configured("slack") is False


def test_notification_processor_process_pending(delivery_service, notification_repository):
    """Test processing pending notifications."""
    processor = NotificationProcessor(delivery_service, notification_repository)

    # Create some queued notifications
    notification_repository.create_notification(
        NotificationRecord(channel="telegram", kind="test", status="queued", summary="Test 1")
    )
    notification_repository.create_notification(
        NotificationRecord(channel="telegram", kind="test", status="queued", summary="Test 2")
    )
    notification_repository.create_notification(
        NotificationRecord(channel="slack", kind="alert", status="queued", summary="Test 3")
    )

    with patch.object(delivery_service, "send_telegram", return_value=True) as mock_tg, \
         patch.object(delivery_service, "send_slack", return_value=True) as mock_slack:
        results = processor.process_pending(limit=10)

    assert results["sent"] == 3
    assert results["failed"] == 0
    assert results["skipped"] == 0
    assert mock_tg.call_count == 2
    assert mock_slack.call_count == 1


def test_notification_processor_skips_unconfigured(notification_repository):
    """Test that unconfigured channels are skipped."""
    # Create a service with Telegram credentials (Slack not configured)
    service = NotificationDeliveryService(telegram_bot_token="token", telegram_chat_id="chat")
    processor = NotificationProcessor(service, notification_repository)

    notification_repository.create_notification(
        NotificationRecord(channel="slack", kind="test", status="queued", summary="Test Slack")
    )
    notification_repository.create_notification(
        NotificationRecord(channel="telegram", kind="test", status="queued", summary="Test Telegram")
    )

    # Mock send_telegram to simulate success
    with patch.object(service, 'send_telegram', return_value=True) as mock_tg:
        results = processor.process_pending(limit=10)

    assert results["sent"] == 1
    assert results["failed"] == 0
    assert results["skipped"] == 1
    mock_tg.assert_called_once()
