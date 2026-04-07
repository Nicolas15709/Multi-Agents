"""
replanner.py - Dynamic re-planning for the multi-agent system.

When tasks repeatedly fail, the DynamicReplanner asks Claude (acting as the
Agent-0 Supervisor) to analyse the failure and produce a revised plan:
  - skip the task
  - replace it with simpler sub-tasks
  - escalate to a human

Usage
-----
    from replanner import DynamicReplanner

    replanner = DynamicReplanner()
    if replanner.should_replan(mission_id, failed_task, all_tasks):
        result = replanner.replan(mission, failed_task, all_tasks, task_repository)
        _apply_replan(result, failed_task, all_tasks, task_repository)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _supervisor_prompt() -> str:
    """Load the supervisor system prompt from prompts/supervisor.AGENTS.md.

    Path resolution: __file__ -> runtime/python -> runtime -> MissionControl -> project root
    The prompts/ directory lives at project root level (3 levels up from this file).
    """
    here = Path(__file__).resolve()
    # runtime/python/replanner.py  ->  up 3 = project root
    project_root = here.parent.parent.parent
    prompt_path = project_root / "prompts" / "supervisor.AGENTS.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    logger.warning("Supervisor prompt not found at %s; using fallback.", prompt_path)
    return (
        "You are Agent-0, the Supervisor of a multi-agent system. "
        "You analyse task failures and decide how to recover."
    )


def _build_context_prompt(
    mission: Dict,
    failed_task: Dict,
    all_tasks: List[Dict],
) -> str:
    """Construct the user-turn message sent to Claude."""
    details: Dict = failed_task.get("details") or {}
    exec_result: Dict = details.get("_exec_result") or {}
    retry_count: int = details.get("retry_count", 0)
    error_msg: str = exec_result.get("error") or "(no error message recorded)"
    summary: str = exec_result.get("summary") or "(no summary)"

    task_status_lines: List[str] = []
    for t in all_tasks:
        t_details = t.get("details") or {}
        t_exec = t_details.get("_exec_result") or {}
        t_error = t_exec.get("error", "")
        skipped = t_details.get("_skipped", False)
        line = (
            f"  - [{t['status']}{'|skipped' if skipped else ''}] "
            f"{t['title']} (id={t['id']}, agent={t['agent_id']})"
        )
        if t_error:
            line += f"  ERROR: {t_error[:120]}"
        task_status_lines.append(line)

    task_table = "\n".join(task_status_lines) if task_status_lines else "  (no tasks)"

    return (
        "## Re-planning Request\n\n"
        f"**Mission goal:** {mission.get('goal', '(unknown)')}\n\n"
        "**Failed task:**\n"
        f"  - id: {failed_task['id']}\n"
        f"  - title: {failed_task['title']}\n"
        f"  - agent: {failed_task.get('agent_id', '?')}\n"
        f"  - retry_count: {retry_count}\n"
        f"  - error: {error_msg}\n"
        f"  - last summary: {summary}\n\n"
        "**All task statuses:**\n"
        f"{task_table}\n\n"
        "## Instructions\n\n"
        "Analyse the failure and decide the best recovery action. "
        "Respond with a single JSON object — no markdown fences, no extra text — "
        "matching this schema:\n\n"
        "```\n"
        "{\n"
        '  "action": "replace_task" | "insert_tasks" | "skip" | "escalate",\n'
        '  "reasoning": "<why you chose this action>",\n'
        '  "new_tasks": [           // required for replace_task / insert_tasks\n'
        "    {\n"
        '      "title": "<task title>",\n'
        '      "agent_id": "<agent-0..agent-4>",\n'
        '      "phase_kind": "<research|design|build|validate|consolidate>",\n'
        '      "goal": "<what the agent must accomplish>",\n'
        '      "depends_on": ["<task_id>", ...]   // may be empty\n'
        "    }\n"
        "  ],\n"
        '  "escalation_reason": "<only when action=escalate>"\n'
        "}\n"
        "```\n\n"
        "Rules:\n"
        "- For `replace_task`: provide new_tasks that fully replace the failed task.\n"
        "- For `insert_tasks`: provide new_tasks to insert before the failed task retries.\n"
        "- For `skip`: set new_tasks to [] and explain in reasoning.\n"
        "- For `escalate`: set new_tasks to [] and fill escalation_reason.\n"
        "Respond with valid JSON only."
    )


def _parse_claude_response(content: str) -> Dict:
    """Extract and parse JSON from Claude's response text."""
    text = content.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first and last fence lines
        inner = []
        in_block = False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            if line.startswith("```") and in_block:
                break
            if in_block:
                inner.append(line)
        text = "\n".join(inner).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Claude JSON response: %s\nRaw text: %s", exc, content[:500])
        return {
            "action": "escalate",
            "reasoning": "Claude returned unparseable JSON.",
            "new_tasks": [],
            "escalation_reason": f"json_parse_error: {exc}",
        }

    # Validate required fields
    action = parsed.get("action")
    valid_actions = {"replace_task", "insert_tasks", "skip", "escalate"}
    if action not in valid_actions:
        logger.warning("Claude returned unknown action '%s'; defaulting to escalate.", action)
        parsed["action"] = "escalate"
        parsed.setdefault("escalation_reason", f"unknown_action:{action}")

    parsed.setdefault("new_tasks", [])
    parsed.setdefault("reasoning", "")
    return parsed


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class DynamicReplanner:
    """Analyses repeated task failures and asks Claude to produce a revised plan."""

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        self.model = model
        self._api_key: Optional[str] = os.environ.get("ANTHROPIC_API_KEY")

    # ------------------------------------------------------------------
    # should_replan
    # ------------------------------------------------------------------

    def should_replan(
        self,
        mission_id: str,
        failed_task: Dict,
        all_tasks: List[Dict],
    ) -> bool:
        """Return True if re-planning is warranted.

        Triggers when:
          - retry_count >= 2, OR
          - the same error message has appeared in multiple failed tasks for
            this mission (repeated systemic failure pattern).
        """
        details: Dict = failed_task.get("details") or {}
        retry_count: int = details.get("retry_count", 0)

        if retry_count >= 2:
            logger.info(
                "should_replan=True for task %s (retry_count=%d >= 2)",
                failed_task.get("id"),
                retry_count,
            )
            return True

        # Check for repeated identical error across mission tasks
        current_error: str = (
            (details.get("_exec_result") or {}).get("error") or ""
        ).strip()

        if current_error:
            error_count = 0
            for t in all_tasks:
                if t.get("mission_id") != mission_id:
                    continue
                if t.get("status") != "failed":
                    continue
                t_error = (
                    ((t.get("details") or {}).get("_exec_result") or {}).get("error") or ""
                ).strip()
                if t_error == current_error:
                    error_count += 1

            if error_count >= 2:
                logger.info(
                    "should_replan=True for task %s (same error seen %d times across mission %s)",
                    failed_task.get("id"),
                    error_count,
                    mission_id,
                )
                return True

        return False

    # ------------------------------------------------------------------
    # replan
    # ------------------------------------------------------------------

    def replan(
        self,
        mission: Dict,
        failed_task: Dict,
        all_tasks: List[Dict],
        task_repository: Any,
    ) -> Dict:
        """Ask Claude to analyse the failure and produce a recovery plan.

        Returns a dict with keys:
            action       : "replace_task" | "insert_tasks" | "escalate" | "skip"
            new_tasks    : list of task descriptors
            reasoning    : str
            escalation_reason : str  (only when action == "escalate")
        """
        if not self._api_key:
            logger.warning("ANTHROPIC_API_KEY not set; escalating without LLM.")
            return {
                "action": "escalate",
                "reasoning": "No LLM configured; cannot auto-replan.",
                "new_tasks": [],
                "escalation_reason": "no_llm_configured",
            }

        system_prompt = _supervisor_prompt()
        user_message = _build_context_prompt(mission, failed_task, all_tasks)

        logger.info(
            "Requesting replan from Claude for task %s (mission %s).",
            failed_task.get("id"),
            mission.get("id"),
        )

        try:
            import anthropic  # local import to keep module loadable without the package

            client = anthropic.Anthropic(api_key=self._api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            raw_text: str = response.content[0].text if response.content else ""
            logger.debug("Claude raw replan response: %s", raw_text[:800])
            result = _parse_claude_response(raw_text)

        except Exception as exc:  # noqa: BLE001
            logger.exception("Claude replan call failed: %s", exc)
            result = {
                "action": "escalate",
                "reasoning": f"Claude API error: {exc}",
                "new_tasks": [],
                "escalation_reason": f"llm_error: {exc}",
            }

        logger.info(
            "Replan decision for task %s: action=%s, new_tasks=%d, reasoning=%s",
            failed_task.get("id"),
            result.get("action"),
            len(result.get("new_tasks") or []),
            result.get("reasoning", "")[:200],
        )
        return result


# ---------------------------------------------------------------------------
# _apply_replan  (helper that mutates the task_repository)
# ---------------------------------------------------------------------------

def _apply_replan(
    replan_result: Dict,
    failed_task: Dict,
    all_tasks: List[Dict],
    task_repository: Any,
) -> List[str]:
    """Apply a replan result to the task_repository.

    Actions:
      - replace_task / insert_tasks:
            * Mark failed_task as skipped (details["_skipped"] = True, status = "failed").
            * Create each new task in the repository.
      - skip:
            * Mark failed_task as skipped.
      - escalate:
            * Mark failed_task details with _escalated = True.

    Returns a list of newly created task IDs.
    """
    try:
        from .utils import new_id
    except ImportError:  # pragma: no cover
        from utils import new_id

    try:
        from .models import Task
    except ImportError:  # pragma: no cover
        from models import Task

    action: str = replan_result.get("action", "escalate")
    new_task_specs: List[Dict] = replan_result.get("new_tasks") or []
    created_ids: List[str] = []

    task_id: str = failed_task["id"]
    mission_id: str = failed_task["mission_id"]

    current_details: Dict = dict(failed_task.get("details") or {})

    if action in ("replace_task", "insert_tasks"):
        # Mark old task as skipped
        current_details["_skipped"] = True
        current_details["_skip_reason"] = replan_result.get("reasoning", "")
        task_repository.update_task_details(task_id, current_details)
        logger.info("Marked task %s as skipped (action=%s).", task_id, action)

        # Create replacement / inserted tasks
        for spec in new_task_specs:
            new_id_val = new_id("task")
            phase_kind = spec.get("phase_kind", "build")
            new_task = Task(
                id=new_id_val,
                mission_id=mission_id,
                agent_id=spec.get("agent_id", "agent-0"),
                title=spec.get("title", "Unnamed task"),
                status="pending",
                depends_on=spec.get("depends_on") or [],
                details={
                    "phase_kind": phase_kind,
                    "goal": spec.get("goal", ""),
                    "acceptance_criteria": spec.get("acceptance_criteria", ""),
                    "retry_count": 0,
                    "_replanned_from": task_id,
                },
            )
            task_repository.create_task(new_task)
            created_ids.append(new_id_val)
            logger.info(
                "Created replacement task %s (%s) for agent %s.",
                new_id_val,
                new_task.title,
                new_task.agent_id,
            )

    elif action == "skip":
        current_details["_skipped"] = True
        current_details["_skip_reason"] = replan_result.get("reasoning", "deliberate skip")
        task_repository.update_task_details(task_id, current_details)
        task_repository.update_task_status(task_id, "failed")
        logger.info("Skipped task %s per replan decision.", task_id)

    elif action == "escalate":
        current_details["_escalated"] = True
        current_details["_escalation_reason"] = replan_result.get("escalation_reason", "")
        task_repository.update_task_details(task_id, current_details)
        logger.warning(
            "Task %s escalated to human: %s",
            task_id,
            replan_result.get("escalation_reason", ""),
        )

    else:
        logger.error("Unknown replan action '%s'; no changes made.", action)

    return created_ids
