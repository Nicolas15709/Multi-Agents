"""Notification delivery service for Telegram and Slack."""

import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class NotificationDeliveryService:
    """Service for delivering notifications to external channels."""

    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    timeout: int = 10

    @classmethod
    def from_env(cls) -> "NotificationDeliveryService":
        """Create service from environment variables."""
        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
        )

    def is_configured(self, channel: str) -> bool:
        """Check if a notification channel is configured."""
        if channel == "telegram":
            return bool(self.telegram_bot_token and self.telegram_chat_id)
        elif channel == "slack":
            return bool(self.slack_webhook_url)
        return False

    def send_telegram(self, summary: str, payload: Dict = None, kind: str = "notification") -> bool:
        """Send a notification via Telegram Bot API."""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.warning("Telegram not configured (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID)")
            return False

        # Build message text
        message = f"<b>{summary}</b>"
        if payload:
            try:
                payload_str = json.dumps(payload, indent=2, ensure_ascii=False)
                message += f"\n\n<pre>{payload_str}</pre>"
            except Exception:
                message += f"\n\nPayload: {payload}"

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        data = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_notification": kind in ("heartbeat", "progress"),
        }

        try:
            resp = requests.post(url, data=data, timeout=self.timeout)
            if resp.status_code == 200:
                logger.info(f"Telegram notification sent: {summary}")
                return True
            else:
                logger.error(f"Telegram API error {resp.status_code}: {resp.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False

    def send_slack(self, summary: str, payload: Dict = None, kind: str = "notification") -> bool:
        """Send a notification via Slack Incoming Webhook."""
        if not self.slack_webhook_url:
            logger.warning("Slack not configured (missing SLACK_WEBHOOK_URL)")
            return False

        # Build Slack message
        text = summary
        if payload:
            try:
                text += f"\n```\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```"
            except Exception:
                text += f"\nPayload: {payload}"

        # Use different colors based on kind
        color = "#36a64f"  # green for normal
        if kind in ("error", "failure", "blocked"):
            color = "#ff0000"  # red
        elif kind in ("warning", "timeout"):
            color = "#ffcc00"  # yellow

        data = {
            "attachments": [
                {
                    "color": color,
                    "text": text,
                    "mrkdwn_in": ["text"],
                }
            ]
        }

        try:
            resp = requests.post(self.slack_webhook_url, json=data, timeout=self.timeout)
            if resp.status_code == 200:
                logger.info(f"Slack notification sent: {summary}")
                return True
            else:
                logger.error(f"Slack webhook error {resp.status_code}: {resp.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def send(self, channel: str, summary: str, payload: Dict = None, kind: str = "notification") -> bool:
        """Send a notification to the specified channel."""
        if channel == "telegram":
            return self.send_telegram(summary, payload, kind)
        elif channel == "slack":
            return self.send_slack(summary, payload, kind)
        else:
            logger.warning(f"Unknown notification channel: {channel}")
            return False


class NotificationProcessor:
    """Processes queued notifications and delivers them."""

    def __init__(self, delivery_service: NotificationDeliveryService, repository):
        self.delivery_service = delivery_service
        self.repository = repository

    def process_pending(self, limit: int = 50) -> Dict[str, int]:
        """
        Process pending notifications up to the limit.
        Returns counts of processed notifications by outcome.
        """
        results = {"sent": 0, "failed": 0, "skipped": 0}

        # Get pending notifications
        pending = self.repository.recent_notifications(limit=limit)
        pending = [n for n in pending if n["status"] == "queued"]

        for notification in pending:
            notification_id = notification["id"]
            channel = notification["channel"]
            kind = notification["kind"]
            summary = notification["summary"]
            payload = notification["payload"]

            if not self.delivery_service.is_configured(channel):
                logger.info(f"Skipping notification {notification_id}: {channel} not configured")
                results["skipped"] += 1
                continue

            success = self.delivery_service.send(channel, summary, payload, kind)

            if success:
                # Could update notification status here if needed
                results["sent"] += 1
            else:
                results["failed"] += 1

        return results
