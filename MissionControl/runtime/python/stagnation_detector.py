"""
StagnationDetector — Identifies when a multi-agent mission is stuck in a
negative-entropy loop (spinning without making real progress).

Detection runs each tick *before* the scheduler advances tasks.  When a
stagnation signal is returned, the caller (TaskRunner / main loop) can act on
the recommendation (retry with a different strategy, escalate, skip, …).

Checks performed
────────────────
1. Repeated error fingerprint — same error string (first 200 chars hashed)
   appearing in 2+ consecutive retries of the same task.
2. Budget burn without progress — tokens_used / max_tokens > 0.6 AND
   zero tasks in done/completed state.
3. LLM loop — same tool-call sequence repeated 3+ times (detected via the
   `iterations` counter stored in _exec_result by AgentExecutor).
4. Timeout — a task has been in "running" state for > 5 consecutive ticks
   with no change in token consumption.
5. Total deadlock — all tasks are blocked/failed and none are running.

Severity escalation
───────────────────
  warning  → heuristics caught something suspicious
  critical → budget > 80 %, OR retries exhausted on a high/critical priority
             task, OR LLM confirms "warning" is actually broken.

Optional LLM audit
──────────────────
When the ANTHROPIC_API_KEY env-var is set and a "warning"-level signal is
found, the detector calls claude-haiku with a compact JSON summary of the
mission state.  The model can upgrade the signal to "critical" or downgrade
it to None (false alarm).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("stagnation_detector")

# ─── Constants ────────────────────────────────────────────────────────────────

_HAIKU_MODEL = "claude-haiku-4-5-20251001"

_REPEATED_ERROR_THRESHOLD = 2        # consecutive retries with same error hash
_BUDGET_BURN_RATIO = 0.60            # token-use fraction that triggers check
_BUDGET_CRITICAL_RATIO = 0.80        # fraction that forces severity=critical
_RUNNING_TICK_TIMEOUT = 5            # ticks a task may stay "running"
_LLM_LOOP_ITERATIONS_THRESHOLD = 3   # repeated tool-call sequences


# ─── Public dataclass ─────────────────────────────────────────────────────────

@dataclass
class StagnationSignal:
    detected: bool
    reason: str          # "repeated_error" | "no_progress" | "budget_burn_no_output" | "llm_loop"
    severity: str        # "warning" | "critical"
    affected_task_id: str
    recommendation: str  # "retry_different_strategy" | "escalate_human" | "skip_task" | "adjust_budget"
    details: Dict


# ─── Internal per-mission state ───────────────────────────────────────────────

@dataclass
class _TaskState:
    """Mutable tracking record kept in memory for one task."""
    # error fingerprint history — list of hashes, one per retry attempt
    error_hashes: List[str] = field(default_factory=list)
    # how many consecutive ticks this task has been "running"
    running_ticks: int = 0
    # token count at the start of the current "running" streak
    tokens_at_run_start: int = 0
    # last seen token count (to detect actual work being done)
    last_tokens_seen: int = 0


@dataclass
class _MissionState:
    """Mutable tracking record kept in memory for one mission."""
    tasks: Dict[str, _TaskState] = field(default_factory=dict)
    # incremented each tick so we can age out stale signals
    tick_count: int = 0

    def get_task(self, task_id: str) -> _TaskState:
        if task_id not in self.tasks:
            self.tasks[task_id] = _TaskState()
        return self.tasks[task_id]


# ─── Helper utilities ─────────────────────────────────────────────────────────

def _error_fingerprint(error_str: str) -> str:
    """Stable 8-char hash of the first 200 characters of an error string."""
    snippet = (error_str or "")[:200]
    return hashlib.sha256(snippet.encode("utf-8", errors="replace")).hexdigest()[:8]


def _exec_result(task: Dict) -> Dict:
    """Safe accessor for task['details']['_exec_result']."""
    return task.get("details", {}).get("_exec_result") or {}


def _exec_status(task: Dict) -> str:
    return task.get("details", {}).get("_exec_status", task.get("status", "pending"))


def _retry_count(task: Dict) -> int:
    return int(task.get("details", {}).get("retry_count", 0))


def _tokens_used(task: Dict) -> int:
    return int(_exec_result(task).get("tokens_used", 0))


def _is_critical_priority(task: Dict) -> bool:
    return task.get("priority", "medium") in {"high", "critical"}


# ─── LLM qualitative audit ────────────────────────────────────────────────────

def _llm_audit(
    mission_id: str,
    tasks: List[Dict],
    signal: StagnationSignal,
    mission_control: Optional[Dict],
) -> Optional[StagnationSignal]:
    """
    Ask claude-haiku to confirm or downgrade a warning-level signal.

    Returns:
      - The original signal upgraded to "critical" if LLM agrees it's broken.
      - None if LLM thinks it's a false alarm.
      - The original signal unchanged if the LLM call fails.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.debug("No ANTHROPIC_API_KEY — skipping LLM audit")
        return signal

    try:
        import anthropic  # noqa: PLC0415
    except ImportError:
        logger.debug("anthropic SDK not installed — skipping LLM audit")
        return signal

    # Build a compact JSON snapshot of the mission state
    task_summaries = []
    for t in tasks:
        res = _exec_result(t)
        task_summaries.append({
            "id": t.get("id"),
            "status": t.get("status"),
            "_exec_status": _exec_status(t),
            "priority": t.get("priority", "medium"),
            "retry_count": _retry_count(t),
            "tokens_used": res.get("tokens_used", 0),
            "error": (res.get("error") or "")[:300],
            "summary": (res.get("summary") or "")[:300],
        })

    prompt_payload = {
        "mission_id": mission_id,
        "heuristic_signal": {
            "reason": signal.reason,
            "severity": signal.severity,
            "affected_task_id": signal.affected_task_id,
            "recommendation": signal.recommendation,
            "details": signal.details,
        },
        "tasks": task_summaries,
        "mission_control_snapshot": mission_control or {},
    }

    system_prompt = (
        "You are a stagnation auditor for a multi-agent task system. "
        "You receive a JSON object describing a heuristic warning and the current task states. "
        "Respond with ONLY a JSON object with two keys:\n"
        '  "verdict": "critical" | "warning" | "none"\n'
        '  "reason": one short sentence\n'
        "Use verdict=critical if the system is genuinely stuck and will not self-recover. "
        "Use verdict=none if this is a transient condition that will likely resolve in 1-2 ticks. "
        "Use verdict=warning to keep the current severity."
    )

    user_content = json.dumps(prompt_payload, default=str)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=_HAIKU_MODEL,
            max_tokens=256,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.strip().startswith("```")
            ).strip()
        audit = json.loads(raw)
        verdict = audit.get("verdict", "warning")
        llm_reason = audit.get("reason", "")
        logger.info(
            "LLM audit verdict=%s reason=%r for mission=%s",
            verdict, llm_reason, mission_id,
        )

        if verdict == "none":
            logger.info("LLM downgraded stagnation signal to none (false alarm)")
            return None

        if verdict == "critical":
            upgraded = StagnationSignal(
                detected=True,
                reason=signal.reason,
                severity="critical",
                affected_task_id=signal.affected_task_id,
                recommendation=signal.recommendation,
                details={**signal.details, "llm_audit_reason": llm_reason},
            )
            return upgraded

        # verdict == "warning" — keep as-is
        return signal

    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM audit failed (%s) — keeping heuristic signal", exc)
        return signal


# ─── Main detector class ──────────────────────────────────────────────────────

class StagnationDetector:
    """
    Detects negative-entropy loops in multi-agent mission execution.

    State is kept per-mission in an in-memory dict.  Call ``reset(mission_id)``
    when a mission completes so memory is released.
    """

    def __init__(self, max_tokens: int = 50_000, llm_audit_enabled: bool = True):
        """
        Parameters
        ----------
        max_tokens:
            Estimated total token budget for the mission.  Used to compute the
            budget-burn ratio.  Can be overridden per-call via mission_control.
        llm_audit_enabled:
            When True (default), call claude-haiku to confirm warning-level
            signals when ANTHROPIC_API_KEY is available.
        """
        self._max_tokens = max_tokens
        self._llm_audit_enabled = llm_audit_enabled
        # mission_id → _MissionState
        self._state: Dict[str, _MissionState] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def check(
        self,
        mission_id: str,
        tasks: List[Dict],
        mission_control: Optional[Dict] = None,
    ) -> Optional[StagnationSignal]:
        """
        Analyse task history for stagnation patterns.

        Returns a ``StagnationSignal`` if the system appears stuck, or ``None``
        if everything looks healthy.

        Parameters
        ----------
        mission_id:
            Identifier of the active mission.
        tasks:
            List of task dicts as stored in the DB / repository.
        mission_control:
            Optional snapshot of mission-level metadata (budget, tick count,
            etc.).  Keys used: ``max_tokens``, ``tick``.
        """
        if not tasks:
            return None

        ms = self._get_mission_state(mission_id)
        ms.tick_count += 1

        # Resolve effective token budget
        max_tokens = self._max_tokens
        if mission_control:
            max_tokens = int(mission_control.get("max_tokens", max_tokens))

        # Aggregate totals
        total_tokens = sum(_tokens_used(t) for t in tasks)
        done_tasks = [
            t for t in tasks
            if t.get("status") in {"done", "completed"}
            or _exec_status(t) in {"done", "completed"}
        ]
        running_tasks = [
            t for t in tasks
            if t.get("status") == "running" or _exec_status(t) == "running"
        ]
        failed_tasks = [
            t for t in tasks
            if t.get("status") == "failed" or _exec_status(t) == "failed"
        ]

        # ── Check 1: Repeated error fingerprint ──────────────────────────────
        signal = self._check_repeated_error(ms, tasks, max_tokens, total_tokens)
        if signal:
            return self._maybe_llm_audit(signal, mission_id, tasks, mission_control)

        # ── Check 2: Budget burn with zero progress ───────────────────────────
        signal = self._check_budget_burn(
            ms, tasks, total_tokens, max_tokens, done_tasks
        )
        if signal:
            return self._maybe_llm_audit(signal, mission_id, tasks, mission_control)

        # ── Check 3: LLM loop (high iteration count) ──────────────────────────
        signal = self._check_llm_loop(ms, tasks, max_tokens, total_tokens)
        if signal:
            return self._maybe_llm_audit(signal, mission_id, tasks, mission_control)

        # ── Check 4: Running timeout (no token progress) ──────────────────────
        signal = self._check_running_timeout(
            ms, tasks, running_tasks, max_tokens, total_tokens
        )
        if signal:
            return self._maybe_llm_audit(signal, mission_id, tasks, mission_control)

        # ── Check 5: Total deadlock ───────────────────────────────────────────
        signal = self._check_deadlock(
            ms, tasks, running_tasks, failed_tasks, done_tasks
        )
        if signal:
            return self._maybe_llm_audit(signal, mission_id, tasks, mission_control)

        # Update running-tick counters for next tick
        self._update_running_ticks(ms, tasks)

        logger.debug(
            "Stagnation check OK — mission=%s tick=%d done=%d/%d tokens=%d",
            mission_id, ms.tick_count, len(done_tasks), len(tasks), total_tokens,
        )
        return None

    def reset(self, mission_id: str) -> None:
        """Release in-memory state for a completed or cancelled mission."""
        if mission_id in self._state:
            del self._state[mission_id]
            logger.debug("Stagnation state reset for mission=%s", mission_id)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_mission_state(self, mission_id: str) -> _MissionState:
        if mission_id not in self._state:
            self._state[mission_id] = _MissionState()
        return self._state[mission_id]

    # ── Check implementations ─────────────────────────────────────────────────

    def _check_repeated_error(
        self,
        ms: _MissionState,
        tasks: List[Dict],
        max_tokens: int,
        total_tokens: int,
    ) -> Optional[StagnationSignal]:
        """
        Check 1: Same error string hash appears in 2+ consecutive retries.
        """
        for task in tasks:
            task_id = task.get("id", "unknown")
            result = _exec_result(task)
            error_str = result.get("error") or ""
            exec_st = _exec_status(task)

            if not error_str or exec_st not in {"failed", "running"}:
                # No error to fingerprint yet — reset history
                ts = ms.get_task(task_id)
                # If task is done, clear error history
                if exec_st in {"done", "completed"}:
                    ts.error_hashes.clear()
                continue

            fingerprint = _error_fingerprint(error_str)
            ts = ms.get_task(task_id)

            # Append only if this is a new retry (not the same tick)
            retry_count = _retry_count(task)
            # Use len(error_hashes) as a proxy for "have we seen this retry?"
            # Grow the list only when retry_count advances
            if len(ts.error_hashes) <= retry_count:
                ts.error_hashes.append(fingerprint)

            # Look at the last N hashes
            recent = ts.error_hashes[-(_REPEATED_ERROR_THRESHOLD + 1):]
            unique_recent = set(recent)
            if len(recent) >= _REPEATED_ERROR_THRESHOLD and len(unique_recent) == 1:
                retries_exhausted = retry_count >= 3
                severity = "critical" if (
                    retries_exhausted
                    or _is_critical_priority(task)
                    or total_tokens / max(max_tokens, 1) >= _BUDGET_CRITICAL_RATIO
                ) else "warning"

                recommendation = (
                    "escalate_human"
                    if retries_exhausted or severity == "critical"
                    else "retry_different_strategy"
                )

                logger.warning(
                    "Stagnation: repeated_error task=%s fingerprint=%s retries=%d severity=%s",
                    task_id, fingerprint, retry_count, severity,
                )
                return StagnationSignal(
                    detected=True,
                    reason="repeated_error",
                    severity=severity,
                    affected_task_id=task_id,
                    recommendation=recommendation,
                    details={
                        "error_fingerprint": fingerprint,
                        "error_preview": error_str[:200],
                        "retry_count": retry_count,
                        "consecutive_identical_errors": len(recent),
                    },
                )
        return None

    def _check_budget_burn(
        self,
        ms: _MissionState,
        tasks: List[Dict],
        total_tokens: int,
        max_tokens: int,
        done_tasks: List[Dict],
    ) -> Optional[StagnationSignal]:
        """
        Check 2: Token budget > 60 % consumed but zero tasks done.
        """
        if max_tokens <= 0 or total_tokens <= 0:
            return None

        ratio = total_tokens / max_tokens
        if ratio < _BUDGET_BURN_RATIO:
            return None
        if done_tasks:
            return None  # Progress is being made — no stagnation

        severity = "critical" if ratio >= _BUDGET_CRITICAL_RATIO else "warning"
        recommendation = "adjust_budget" if severity == "warning" else "escalate_human"

        logger.warning(
            "Stagnation: budget_burn_no_output mission tokens=%d max=%d ratio=%.2f",
            total_tokens, max_tokens, ratio,
        )
        return StagnationSignal(
            detected=True,
            reason="budget_burn_no_output",
            severity=severity,
            affected_task_id="",
            recommendation=recommendation,
            details={
                "tokens_used": total_tokens,
                "max_tokens": max_tokens,
                "burn_ratio": round(ratio, 4),
                "done_task_count": 0,
            },
        )

    def _check_llm_loop(
        self,
        ms: _MissionState,
        tasks: List[Dict],
        max_tokens: int,
        total_tokens: int,
    ) -> Optional[StagnationSignal]:
        """
        Check 3: Same tool-call sequence repeated 3+ times.

        AgentExecutor stores the iteration count inside _exec_result["iterations"]
        when it detects a repeated tool sequence.  We use that as the signal.
        """
        for task in tasks:
            task_id = task.get("id", "unknown")
            result = _exec_result(task)
            iterations = result.get("iterations", 0)
            if iterations is None:
                iterations = 0

            # Detect loop: iterations >= threshold AND task still running
            exec_st = _exec_status(task)
            if (
                int(iterations) >= _LLM_LOOP_ITERATIONS_THRESHOLD
                and exec_st == "running"
            ):
                severity = "critical" if (
                    _is_critical_priority(task)
                    or total_tokens / max(max_tokens, 1) >= _BUDGET_CRITICAL_RATIO
                ) else "warning"

                logger.warning(
                    "Stagnation: llm_loop task=%s iterations=%d severity=%s",
                    task_id, iterations, severity,
                )
                return StagnationSignal(
                    detected=True,
                    reason="llm_loop",
                    severity=severity,
                    affected_task_id=task_id,
                    recommendation=(
                        "escalate_human"
                        if severity == "critical"
                        else "retry_different_strategy"
                    ),
                    details={
                        "iterations": int(iterations),
                        "threshold": _LLM_LOOP_ITERATIONS_THRESHOLD,
                        "exec_status": exec_st,
                    },
                )
        return None

    def _check_running_timeout(
        self,
        ms: _MissionState,
        tasks: List[Dict],
        running_tasks: List[Dict],
        max_tokens: int,
        total_tokens: int,
    ) -> Optional[StagnationSignal]:
        """
        Check 4: A task has been "running" for > N consecutive ticks
        with no change in token consumption.
        """
        for task in running_tasks:
            task_id = task.get("id", "unknown")
            ts = ms.get_task(task_id)
            current_tokens = _tokens_used(task)

            ts.running_ticks += 1

            # If token count has changed since last tick, the agent is alive
            if current_tokens != ts.last_tokens_seen:
                ts.running_ticks = 1  # reset streak; there was progress
                ts.tokens_at_run_start = current_tokens
            ts.last_tokens_seen = current_tokens

            if ts.running_ticks > _RUNNING_TICK_TIMEOUT:
                severity = "critical" if (
                    _is_critical_priority(task)
                    or total_tokens / max(max_tokens, 1) >= _BUDGET_CRITICAL_RATIO
                ) else "warning"

                logger.warning(
                    "Stagnation: no_progress task=%s running_ticks=%d severity=%s",
                    task_id, ts.running_ticks, severity,
                )
                return StagnationSignal(
                    detected=True,
                    reason="no_progress",
                    severity=severity,
                    affected_task_id=task_id,
                    recommendation=(
                        "escalate_human"
                        if severity == "critical"
                        else "retry_different_strategy"
                    ),
                    details={
                        "running_ticks": ts.running_ticks,
                        "timeout_threshold": _RUNNING_TICK_TIMEOUT,
                        "tokens_unchanged": current_tokens,
                    },
                )
        return None

    def _check_deadlock(
        self,
        ms: _MissionState,
        tasks: List[Dict],
        running_tasks: List[Dict],
        failed_tasks: List[Dict],
        done_tasks: List[Dict],
    ) -> Optional[StagnationSignal]:
        """
        Check 5: All tasks are blocked or failed and none are running.
        """
        if running_tasks:
            return None
        if len(done_tasks) == len(tasks):
            return None  # All done — healthy terminal state

        pending_tasks = [
            t for t in tasks
            if t.get("status") == "pending" and _exec_status(t) not in {"running", "done", "completed", "failed"}
        ]
        if pending_tasks:
            return None  # There are still tasks that haven't been attempted

        # All non-done tasks are either failed or in a blocked state
        blocked_tasks = [
            t for t in tasks
            if t.get("status") in {"blocked", "failed"}
            or _exec_status(t) in {"failed"}
        ]

        if not blocked_tasks and not failed_tasks:
            return None

        # Check that no task can make progress: all non-done tasks are stuck
        all_stuck = not running_tasks and not pending_tasks
        if not all_stuck:
            return None

        critical_failed = [t for t in failed_tasks if _is_critical_priority(t)]
        severity = "critical" if critical_failed else "warning"

        worst_task_id = (
            critical_failed[0].get("id", "")
            if critical_failed
            else (failed_tasks[0].get("id", "") if failed_tasks else "")
        )

        logger.warning(
            "Stagnation: deadlock — no_running mission tasks=%d failed=%d done=%d severity=%s",
            len(tasks), len(failed_tasks), len(done_tasks), severity,
        )
        return StagnationSignal(
            detected=True,
            reason="no_progress",
            severity=severity,
            affected_task_id=worst_task_id,
            recommendation="escalate_human" if severity == "critical" else "skip_task",
            details={
                "total_tasks": len(tasks),
                "done_tasks": len(done_tasks),
                "failed_tasks": len(failed_tasks),
                "blocked_tasks": len(blocked_tasks),
                "running_tasks": 0,
            },
        )

    # ── Tick-end state update ─────────────────────────────────────────────────

    def _update_running_ticks(self, ms: _MissionState, tasks: List[Dict]) -> None:
        """
        For tasks that are NOT running, reset their running-tick counter so we
        don't carry stale values across state transitions.
        """
        for task in tasks:
            task_id = task.get("id", "unknown")
            exec_st = _exec_status(task)
            if exec_st != "running":
                if task_id in ms.tasks:
                    ms.tasks[task_id].running_ticks = 0

    # ── LLM audit gate ────────────────────────────────────────────────────────

    def _maybe_llm_audit(
        self,
        signal: StagnationSignal,
        mission_id: str,
        tasks: List[Dict],
        mission_control: Optional[Dict],
    ) -> Optional[StagnationSignal]:
        """
        If the signal is "warning"-level and LLM audit is enabled, call the
        haiku model to confirm or downgrade it.  Critical signals are returned
        immediately without an extra API call.
        """
        if signal.severity == "critical":
            logger.info(
                "Stagnation signal severity=critical — skipping LLM audit "
                "(reason=%s task=%s)",
                signal.reason, signal.affected_task_id,
            )
            return signal

        if not self._llm_audit_enabled:
            return signal

        if not os.environ.get("ANTHROPIC_API_KEY"):
            logger.debug("LLM audit skipped — no ANTHROPIC_API_KEY")
            return signal

        return _llm_audit(mission_id, tasks, signal, mission_control)
