"""intervention_policy.py — Configurable intervention threshold engine.

Decides for each significant system event whether to:
  - auto-proceed   ("auto")
  - notify the human ("notify")
  - halt execution  ("halt")

Configuration priority (highest to lowest):
  1. Dict passed to InterventionPolicy(config=...)
  2. MISSION_CONTROL_POLICY_JSON environment variable (JSON string)
  3. Hard-coded DEFAULT_POLICY

Usage
-----
    from intervention_policy import get_default_policy, PolicyDecision

    decision = get_default_policy().evaluate("budget_80pct", {
        "mission_id": "m-123",
        "agent_id": "a-456",
        "estimated_cost_cents": 800,
    })
    if decision.action == "halt":
        raise RuntimeError(decision.reason)
"""

from __future__ import annotations

import json
import logging
import os
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_POLICY: Dict[str, Dict[str, str]] = {
    # event_type                 action      urgency
    "task_failed_max_retries":  {"action": "notify", "urgency": "medium"},
    "budget_80pct":             {"action": "notify", "urgency": "high"},
    "stagnation_critical":      {"action": "halt",   "urgency": "high"},
    "specialist_hire_request":  {"action": "auto",   "urgency": "low"},   # auto-approve hires
    "external_action_git_push": {"action": "notify", "urgency": "medium"},
    "external_action_publish":  {"action": "halt",   "urgency": "high"},
    "mission_cost_threshold":   {"action": "halt",   "urgency": "high"},
    "agent_blocked":            {"action": "notify", "urgency": "low"},
}

# Notify channel matrix: urgency → default channel
_URGENCY_CHANNEL_MAP: Dict[str, str] = {
    "low":    "dashboard",
    "medium": "telegram",
    "high":   "both",
}

# Action escalation order (used when upgrading a decision)
_ACTION_RANK: Dict[str, int] = {
    "auto":   0,
    "notify": 1,
    "halt":   2,
}

_URGENCY_RANK: Dict[str, int] = {
    "low":    0,
    "medium": 1,
    "high":   2,
}

# Cost risk threshold (cents).  Configurable via policy key "cost_risk_threshold_cents".
_DEFAULT_COST_THRESHOLD_CENTS: int = 500   # $5.00

# Working-hours window used by _evaluate_time_risk.
_WORK_HOUR_START: int = 9   # inclusive
_WORK_HOUR_END: int = 18    # exclusive (i.e., up to 17:59)

# Audit log capacity
_AUDIT_LOG_MAXLEN: int = 500


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PolicyDecision:
    """Result returned by InterventionPolicy.evaluate()."""

    action: str          # "auto" | "notify" | "halt"
    reason: str
    notify_channel: str  # "telegram" | "dashboard" | "both" | "none"
    urgency: str         # "low" | "medium" | "high"

    def as_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class AuditEntry:
    """A single record in the PolicyAuditLog."""

    timestamp: str          # ISO-8601 UTC
    event_type: str
    mission_id: str
    agent_id: str
    task_id: str
    action: str
    urgency: str
    notify_channel: str
    reason: str
    context_snapshot: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class PolicyAuditLog:
    """Thread-safe in-memory rotating deque of the last 500 policy decisions.

    The dashboard can call ``entries()`` to fetch all records for display.
    """

    def __init__(self, maxlen: int = _AUDIT_LOG_MAXLEN) -> None:
        self._log: Deque[AuditEntry] = deque(maxlen=maxlen)

    # ------------------------------------------------------------------
    def record(
        self,
        event_type: str,
        context: Dict[str, Any],
        decision: PolicyDecision,
    ) -> None:
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            mission_id=str(context.get("mission_id", "")),
            agent_id=str(context.get("agent_id", "")),
            task_id=str(context.get("task_id", "")),
            action=decision.action,
            urgency=decision.urgency,
            notify_channel=decision.notify_channel,
            reason=decision.reason,
            context_snapshot=dict(context),
        )
        self._log.append(entry)
        logger.debug(
            "policy_audit | event=%s action=%s urgency=%s mission=%s",
            event_type,
            decision.action,
            decision.urgency,
            entry.mission_id,
        )

    def entries(self) -> List[Dict[str, Any]]:
        """Return a list (newest-last) of all audit entries as plain dicts."""
        return [e.as_dict() for e in self._log]

    def clear(self) -> None:
        self._log.clear()

    def __len__(self) -> int:
        return len(self._log)


# ---------------------------------------------------------------------------
# Policy engine
# ---------------------------------------------------------------------------

class InterventionPolicy:
    """Evaluates system events against a configurable rule set and returns a
    :class:`PolicyDecision` describing how the caller should proceed.

    Config schema (JSON object or Python dict)
    ------------------------------------------
    Top-level keys are event_type strings from DEFAULT_POLICY (or custom
    event types).  Each value is a dict with optional keys:

        {
            "action": "auto" | "notify" | "halt",
            "urgency": "low" | "medium" | "high",
            "notify_channel": "telegram" | "dashboard" | "both" | "none"
        }

    Additionally the following meta-keys are supported at the top level:

        "cost_risk_threshold_cents": int   — cost above which action is upgraded
        "work_hour_start": int             — start of working hours (default 9)
        "work_hour_end": int               — end of working hours (default 18)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._audit_log = PolicyAuditLog()
        self._rules: Dict[str, Dict[str, str]] = dict(DEFAULT_POLICY)
        self._cost_threshold: int = _DEFAULT_COST_THRESHOLD_CENTS
        self._work_hour_start: int = _WORK_HOUR_START
        self._work_hour_end: int = _WORK_HOUR_END

        if config:
            self._apply_config(config)
            logger.info("InterventionPolicy initialised with custom config (%d rules)", len(self._rules))
        else:
            logger.info("InterventionPolicy initialised with DEFAULT_POLICY (%d rules)", len(self._rules))

    # ------------------------------------------------------------------
    # Class-method constructors
    # ------------------------------------------------------------------

    @classmethod
    def load_from_env(cls) -> "InterventionPolicy":
        """Read ``MISSION_CONTROL_POLICY_JSON`` environment variable and
        construct an :class:`InterventionPolicy` from it.

        Falls back to defaults when the variable is absent or invalid JSON.
        """
        raw = os.getenv("MISSION_CONTROL_POLICY_JSON", "")
        if not raw:
            logger.debug("MISSION_CONTROL_POLICY_JSON not set; using defaults")
            return cls()
        try:
            config = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("MISSION_CONTROL_POLICY_JSON parse error (%s); using defaults", exc)
            return cls()
        if not isinstance(config, dict):
            logger.warning("MISSION_CONTROL_POLICY_JSON is not a JSON object; using defaults")
            return cls()
        logger.info("InterventionPolicy loaded from MISSION_CONTROL_POLICY_JSON")
        return cls(config=config)

    @classmethod
    def load_from_file(cls, path: str) -> "InterventionPolicy":
        """Read a JSON file at *path* and construct an :class:`InterventionPolicy`.

        Falls back to defaults when the file is missing or contains invalid JSON.
        """
        try:
            with open(path, "r", encoding="utf-8") as fh:
                config = json.load(fh)
        except FileNotFoundError:
            logger.warning("Policy config file not found: %s; using defaults", path)
            return cls()
        except json.JSONDecodeError as exc:
            logger.warning("Policy config file parse error (%s) in %s; using defaults", exc, path)
            return cls()
        if not isinstance(config, dict):
            logger.warning("Policy config file %s is not a JSON object; using defaults", path)
            return cls()
        logger.info("InterventionPolicy loaded from file: %s", path)
        return cls(config=config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, event_type: str, context: Dict[str, Any]) -> PolicyDecision:
        """Main decision point.  Called before any significant agent action.

        Parameters
        ----------
        event_type:
            One of the well-known event strings (e.g. ``"budget_80pct"``) or
            any custom string registered in the policy config.
        context:
            Arbitrary key/value pairs describing the event.  Well-known keys:
            ``mission_id``, ``agent_id``, ``task_id``, ``estimated_cost_cents``,
            ``action_kind``, ``retry_count``, ``severity``.

        Returns
        -------
        PolicyDecision
        """
        # 1. Resolve effective event_type for external_action sub-types
        resolved_type = self._resolve_event_type(event_type, context)

        # 2. Look up base rule
        rule = self._rules.get(resolved_type) or self._rules.get(event_type) or {}
        base_action: str = rule.get("action", "notify")
        base_urgency: str = rule.get("urgency", "medium")

        # Validate
        if base_action not in _ACTION_RANK:
            logger.warning("Unknown action %r in rule for %r; defaulting to 'notify'", base_action, resolved_type)
            base_action = "notify"
        if base_urgency not in _URGENCY_RANK:
            logger.warning("Unknown urgency %r in rule for %r; defaulting to 'medium'", base_urgency, resolved_type)
            base_urgency = "medium"

        reason_parts: List[str] = [
            f"Event '{resolved_type}' matched rule action='{base_action}' urgency='{base_urgency}'"
        ]

        # 3. Cost risk upgrade
        cost_action, cost_urgency, cost_reason = self._evaluate_cost_risk(context)
        if cost_reason:
            reason_parts.append(cost_reason)
        final_action = _max_action(base_action, cost_action)
        final_urgency = _max_urgency(base_urgency, cost_urgency)

        # 4. Time risk upgrade (urgency only)
        time_urgency, time_reason = self._evaluate_time_risk(context)
        if time_reason:
            reason_parts.append(time_reason)
        final_urgency = _max_urgency(final_urgency, time_urgency)

        # 5. Resolve notification channel
        # Config rule may override; otherwise derive from urgency
        if rule.get("notify_channel"):
            notify_channel = rule["notify_channel"]
        else:
            notify_channel = self.get_notification_channels_str(final_action, final_urgency)

        reason = " | ".join(reason_parts)

        decision = PolicyDecision(
            action=final_action,
            reason=reason,
            notify_channel=notify_channel,
            urgency=final_urgency,
        )

        logger.info(
            "policy.evaluate event=%s resolved=%s action=%s urgency=%s channel=%s",
            event_type,
            resolved_type,
            decision.action,
            decision.urgency,
            decision.notify_channel,
        )

        self._audit_log.record(event_type, context, decision)
        return decision

    def get_notification_channels(self, decision: PolicyDecision) -> List[str]:
        """Return a list of channel names to use for *decision*.

        Examples: ``["telegram"]``, ``["telegram", "dashboard"]``, ``[]``
        """
        return _channel_str_to_list(decision.notify_channel)

    def get_notification_channels_str(self, action: str, urgency: str) -> str:
        """Return the canonical channel string for a given (action, urgency) pair."""
        if action == "auto":
            return "none"
        return _URGENCY_CHANNEL_MAP.get(urgency, "dashboard")

    @property
    def audit_log(self) -> PolicyAuditLog:
        """Access to the rotating audit log (last 500 entries)."""
        return self._audit_log

    def describe_rules(self) -> Dict[str, Dict[str, str]]:
        """Return a copy of the effective rule table for inspection/debugging."""
        return dict(self._rules)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_config(self, config: Dict[str, Any]) -> None:
        """Merge *config* into the rule table and apply meta-settings."""
        # Meta keys
        if "cost_risk_threshold_cents" in config:
            try:
                self._cost_threshold = int(config["cost_risk_threshold_cents"])
            except (TypeError, ValueError) as exc:
                logger.warning("Invalid cost_risk_threshold_cents: %s", exc)

        if "work_hour_start" in config:
            try:
                self._work_hour_start = int(config["work_hour_start"])
            except (TypeError, ValueError) as exc:
                logger.warning("Invalid work_hour_start: %s", exc)

        if "work_hour_end" in config:
            try:
                self._work_hour_end = int(config["work_hour_end"])
            except (TypeError, ValueError) as exc:
                logger.warning("Invalid work_hour_end: %s", exc)

        # Rule overrides — every other key is treated as an event_type rule
        meta_keys = {"cost_risk_threshold_cents", "work_hour_start", "work_hour_end"}
        for key, value in config.items():
            if key in meta_keys:
                continue
            if not isinstance(value, dict):
                logger.warning("Policy config key %r has non-dict value; skipping", key)
                continue
            # Merge into existing rule (don't clobber unspecified fields)
            existing = dict(self._rules.get(key, {}))
            existing.update(value)
            self._rules[key] = existing
            logger.debug("Policy rule updated: %s -> %s", key, existing)

    def _resolve_event_type(self, event_type: str, context: Dict[str, Any]) -> str:
        """Refine a generic event_type using context when possible.

        ``"external_action"`` is dispatched to ``"external_action_<action_kind>"``
        if that key exists in the rule table.
        """
        if event_type == "external_action":
            action_kind = str(context.get("action_kind", "")).lower().replace(" ", "_")
            if action_kind:
                candidate = f"external_action_{action_kind}"
                if candidate in self._rules:
                    logger.debug("Resolved event_type %r -> %r via action_kind", event_type, candidate)
                    return candidate
        return event_type

    def _evaluate_cost_risk(
        self, context: Dict[str, Any]
    ) -> tuple[str, str, str]:
        """Return (action_upgrade, urgency_upgrade, reason) based on cost.

        If ``estimated_cost_cents`` in *context* exceeds the threshold, the
        action is upgraded to at least ``"notify"`` and urgency to ``"high"``.
        """
        cost = context.get("estimated_cost_cents")
        if cost is None:
            return "auto", "low", ""
        try:
            cost_int = int(cost)
        except (TypeError, ValueError):
            logger.debug("estimated_cost_cents is not numeric: %r", cost)
            return "auto", "low", ""

        if cost_int > self._cost_threshold:
            reason = (
                f"Cost risk: estimated_cost_cents={cost_int} exceeds threshold={self._cost_threshold}"
            )
            logger.info("cost_risk triggered: %s", reason)
            return "notify", "high", reason

        return "auto", "low", ""

    def _evaluate_time_risk(
        self, context: Dict[str, Any]  # noqa: ARG002 — reserved for future use
    ) -> tuple[str, str]:
        """Return (urgency_upgrade, reason) based on current wall-clock time.

        Events that occur outside the configured working-hours window have
        their urgency upgraded to ``"high"`` so the human is more likely to
        notice them promptly.
        """
        now_hour = datetime.now().hour  # local time
        in_hours = self._work_hour_start <= now_hour < self._work_hour_end
        if not in_hours:
            reason = (
                f"Time risk: current hour {now_hour:02d}:xx is outside "
                f"working hours {self._work_hour_start:02d}:00–{self._work_hour_end:02d}:00"
            )
            logger.debug("time_risk triggered: %s", reason)
            return "high", reason
        return "low", ""


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _max_action(a: str, b: str) -> str:
    """Return whichever action has the higher escalation rank."""
    return a if _ACTION_RANK.get(a, 1) >= _ACTION_RANK.get(b, 1) else b


def _max_urgency(a: str, b: str) -> str:
    """Return whichever urgency level is higher."""
    return a if _URGENCY_RANK.get(a, 1) >= _URGENCY_RANK.get(b, 1) else b


def _channel_str_to_list(channel: str) -> List[str]:
    """Convert a channel string to a list of individual channel names."""
    if channel == "none" or not channel:
        return []
    if channel == "both":
        return ["telegram", "dashboard"]
    return [channel]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_policy: Optional[InterventionPolicy] = None


def get_default_policy() -> InterventionPolicy:
    """Return the module-level singleton InterventionPolicy.

    On first call the policy is initialised from ``MISSION_CONTROL_POLICY_JSON``
    if that env var is set, otherwise from hard-coded defaults.
    """
    global _default_policy
    if _default_policy is None:
        _default_policy = InterventionPolicy.load_from_env()
        logger.info("InterventionPolicy singleton created")
    return _default_policy


def reset_default_policy(policy: Optional[InterventionPolicy] = None) -> None:
    """Replace (or clear) the module-level singleton.  Primarily for tests."""
    global _default_policy
    _default_policy = policy
