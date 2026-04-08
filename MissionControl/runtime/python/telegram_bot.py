"""Telegram bot listener — long-polling incoming messages to create missions.

Runs as a daemon thread alongside the main runtime loop.
Only stdlib is used (urllib) — no third-party Telegram SDK required.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

logger = logging.getLogger("telegram_bot")


class TelegramBotListener:
    """Listen for Telegram messages and dispatch them to the mission system."""

    POLL_TIMEOUT = 30  # seconds for long-polling getUpdates
    RETRY_DELAY = 5    # seconds to wait after a network error
    HELP_TEXT = (
        "🤖 *Virtual Agency Bot*\n\n"
        "Available commands:\n"
        "  /status — active mission count\n"
        "  /missions — last 5 missions\n"
        "  /pause <id> — pause a mission\n"
        "  /help — this message\n\n"
        "Send any other text to create a new mission."
    )

    def __init__(self, token: str, chat_id: str, mission_service, mission_repository):
        self._token = token.strip() if token else ""
        self._chat_id = str(chat_id).strip() if chat_id else ""
        self._mission_service = mission_service
        self._mission_repository = mission_repository
        self._enabled = bool(self._token)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._offset: int = 0

    # ── Public API ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Launch the daemon polling thread (no-op if token not configured)."""
        if not self._enabled:
            logger.info("Telegram bot disabled — TELEGRAM_BOT_TOKEN not set")
            return
        if not self._chat_id:
            logger.warning("Telegram bot: TELEGRAM_CHAT_ID not set — all chats will be rejected")

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, name="telegram-bot", daemon=True)
        self._thread.start()
        logger.info("Telegram bot listener started (chat_id=%s)", self._chat_id or "ANY")

    def stop(self) -> None:
        """Signal the polling thread to stop (best-effort)."""
        self._running = False

    def summary(self) -> dict:
        status = "idle"
        if self._enabled:
            status = "running" if (self._thread and self._thread.is_alive()) else "stopped"
        return {
            "enabled": self._enabled,
            "status": status,
            "chat_id_configured": bool(self._chat_id),
        }

    # ── Internal polling loop ───────────────────────────────────────────────

    def _poll_loop(self) -> None:
        while self._running:
            try:
                updates = self._get_updates()
                for update in updates:
                    self._process_update(update)
            except Exception as exc:
                logger.error("Telegram poll error: %s — retrying in %ds", exc, self.RETRY_DELAY)
                time.sleep(self.RETRY_DELAY)

    def _get_updates(self) -> list:
        """Call getUpdates with long-polling and advance the offset."""
        params = {
            "offset": self._offset,
            "timeout": self.POLL_TIMEOUT,
            "allowed_updates": json.dumps(["message"]),
        }
        url = self._api_url("getUpdates") + "?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=self.POLL_TIMEOUT + 5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            logger.error("getUpdates HTTP %s: %s", exc.code, exc.reason)
            return []
        except OSError as exc:
            logger.error("getUpdates network error: %s", exc)
            time.sleep(self.RETRY_DELAY)
            return []

        if not data.get("ok"):
            logger.error("getUpdates not ok: %s", data)
            return []

        results = data.get("result", [])
        if results:
            self._offset = results[-1]["update_id"] + 1
        return results

    def _process_update(self, update: dict) -> None:
        message = update.get("message") or update.get("edited_message")
        if not message:
            return
        sender_chat_id = str(message.get("chat", {}).get("id", ""))
        text = (message.get("text") or "").strip()
        if not text:
            return

        # Security: only accept messages from the configured chat
        if self._chat_id and sender_chat_id != self._chat_id:
            logger.warning("Rejected message from unauthorized chat_id=%s", sender_chat_id)
            return

        try:
            self._handle_message(text, sender_chat_id)
        except Exception as exc:
            logger.error("Error handling message %r: %s", text, exc)
            self._send("❌ Error processing your request. Check logs for details.")

    def _handle_message(self, text: str, chat_id: str) -> None:
        """Dispatch a message to the appropriate handler."""
        lower = text.lower().strip()

        if lower == "/help":
            self._send(self.HELP_TEXT)

        elif lower == "/status":
            self._cmd_status()

        elif lower == "/missions":
            self._cmd_missions()

        elif lower.startswith("/pause"):
            parts = text.split(maxsplit=1)
            mission_id = parts[1].strip() if len(parts) > 1 else ""
            self._cmd_pause(mission_id)

        elif text.startswith("/"):
            self._send(
                "❓ Unknown command. Send /help to see available commands."
            )

        else:
            self._cmd_create_mission(text)

    # ── Command handlers ────────────────────────────────────────────────────

    def _cmd_status(self) -> None:
        try:
            missions = self._mission_repository.list_missions()
            active = [m for m in missions if m.get("status") not in ("completed", "failed", "cancelled")]
            self._send(
                f"📊 *System Status*\n\n"
                f"Active missions: *{len(active)}*\n"
                f"Total missions: *{len(missions)}*"
            )
        except Exception as exc:
            logger.error("_cmd_status error: %s", exc)
            self._send("❌ Could not retrieve status.")

    def _cmd_missions(self) -> None:
        try:
            missions = self._mission_repository.list_missions()
            recent = missions[-5:] if len(missions) > 5 else missions
            recent = list(reversed(recent))  # newest first
            if not recent:
                self._send("📭 No missions found.")
                return

            STATUS_EMOJI = {
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫",
                "active": "🔄",
                "planning": "📝",
                "needs_human": "⚠️",
                "paused": "⏸️",
            }
            lines = ["📋 *Last 5 Missions*\n"]
            for m in recent:
                status = m.get("status", "unknown")
                emoji = STATUS_EMOJI.get(status, "❓")
                mid = m.get("id", "?")
                title = (m.get("title") or "Untitled")[:50]
                lines.append(f"{emoji} `{mid[:8]}` — {title}\n    Status: {status}")
            self._send("\n".join(lines))
        except Exception as exc:
            logger.error("_cmd_missions error: %s", exc)
            self._send("❌ Could not retrieve mission list.")

    def _cmd_pause(self, mission_id: str) -> None:
        if not mission_id:
            self._send("⚠️ Usage: /pause <mission_id>")
            return
        try:
            mission = self._mission_repository.get_mission(mission_id)
            if not mission:
                # Try prefix match
                all_missions = self._mission_repository.list_missions()
                matches = [m for m in all_missions if m.get("id", "").startswith(mission_id)]
                if len(matches) == 1:
                    mission = matches[0]
                    mission_id = mission["id"]
                elif len(matches) > 1:
                    self._send(f"⚠️ Ambiguous ID prefix — {len(matches)} missions match. Provide more characters.")
                    return
                else:
                    self._send(f"❌ Mission `{mission_id}` not found.")
                    return

            current_status = mission.get("status", "")
            if current_status in ("completed", "failed", "cancelled"):
                self._send(f"⚠️ Mission `{mission_id[:8]}` is already *{current_status}* and cannot be paused.")
                return

            self._mission_repository.update_mission_status(mission_id, "paused")
            title = (mission.get("title") or "Untitled")[:50]
            self._send(f"⏸️ Mission paused successfully.\n\n`{mission_id[:8]}` — {title}")
        except Exception as exc:
            logger.error("_cmd_pause error: %s", exc)
            self._send("❌ Could not pause mission.")

    def _cmd_create_mission(self, text: str) -> None:
        try:
            result = self._mission_service.submit_mission(
                title=text[:80],
                goal=text,
                mode="general_operating_request",
                priority="medium",
                source="telegram",
                allow_24x7=True,
                schedule="telegram:manual",
            )
            mission_id = result.get("mission_id", "?")
            self._send(
                f"✅ *Mission created!*\n\n"
                f"ID: `{mission_id[:8]}`\n"
                f"Goal: {text[:120]}"
            )
            logger.info("Mission created from Telegram: %s", mission_id)
        except Exception as exc:
            logger.error("_cmd_create_mission error: %s", exc)
            self._send("❌ Could not create mission. Please try again.")

    # ── Telegram API helpers ────────────────────────────────────────────────

    def _api_url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self._token}/{method}"

    def _send(self, text: str) -> None:
        """Send a text message to the configured chat."""
        if not self._chat_id:
            logger.warning("Cannot send Telegram message — TELEGRAM_CHAT_ID not configured")
            return
        payload = json.dumps({
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }).encode("utf-8")
        req = urllib.request.Request(
            self._api_url("sendMessage"),
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if not result.get("ok"):
                    logger.error("sendMessage not ok: %s", result)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            logger.error("sendMessage HTTP %s: %s — %s", exc.code, exc.reason, body)
        except OSError as exc:
            logger.error("sendMessage network error: %s", exc)


def create_from_env(mission_service, mission_repository) -> TelegramBotListener:
    """Construct a TelegramBotListener from environment variables."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    return TelegramBotListener(
        token=token,
        chat_id=chat_id,
        mission_service=mission_service,
        mission_repository=mission_repository,
    )
