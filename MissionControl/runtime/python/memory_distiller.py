"""
Punto 2 — Memory Distillation
==============================
After a mission completes (or periodically), this module reads task outputs
from SQLite and asks Claude to produce a concise Markdown summary that gets
appended to the project MEMORY.md.

This prevents context drift: agents always have a distilled, up-to-date
long-term record instead of fragmented raw logs.

Usage:
    distiller = MemoryDistiller()
    distiller.distill_mission(mission_id, mission_repo, task_repo)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("memory_distiller")

_MEMORY_FILE = Path(__file__).resolve().parent.parent.parent / "MEMORY.md"
_MAX_TASK_OUTPUT_CHARS = 2000   # Truncate long outputs before sending to LLM
_DISTILL_MODEL = "claude-haiku-4-5-20251001"   # Cheap + fast for summarization


# ─── Distiller ────────────────────────────────────────────────────────────────

class MemoryDistiller:
    """
    Reads mission + task data from the DB, calls Claude to produce a
    concise memory entry, and appends it to MEMORY.md.
    """

    def __init__(self, memory_file: Path = _MEMORY_FILE):
        self._memory_file = memory_file
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic  # noqa: PLC0415
                self._client = anthropic.Anthropic(
                    api_key=os.environ.get("ANTHROPIC_API_KEY", "")
                )
            except ImportError:
                raise RuntimeError("anthropic SDK not installed")
        return self._client

    # ── Public API ────────────────────────────────────────────────────────────

    def distill_mission(
        self,
        mission_id: str,
        mission_repository,
        task_repository,
    ) -> Optional[str]:
        """
        Distill a completed mission into a MEMORY.md entry.
        Returns the generated markdown string, or None if distillation failed.
        """
        mission = mission_repository.get_mission(mission_id)
        if not mission:
            logger.warning("Distill failed: mission %s not found", mission_id)
            return None

        tasks = task_repository.list_tasks_for_mission(mission_id)
        if not tasks:
            logger.info("No tasks to distill for mission %s", mission_id)
            return None

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            # Fallback: write a plain summary without LLM
            entry = self._plain_summary(mission, tasks)
        else:
            try:
                entry = self._llm_summary(mission, tasks)
            except Exception as exc:
                logger.error("LLM distillation failed: %s — using plain summary", exc)
                entry = self._plain_summary(mission, tasks)

        self._append_to_memory_file(entry)
        logger.info("Memory distilled for mission %s (%d chars)", mission_id, len(entry))
        return entry

    # ── Summary builders ──────────────────────────────────────────────────────

    def _llm_summary(self, mission: Dict, tasks: List[Dict]) -> str:
        """Ask Claude to write a structured memory entry."""
        client = self._get_client()
        context = self._build_context(mission, tasks)

        prompt = f"""You are a knowledge distillation system for a multi-agent AI team.

Given the following completed mission data, write a concise Markdown memory entry that future agents can use as context.

The entry must follow this exact structure:
```
### [YYYY-MM-DD] Mission: <title>
**Goal:** <one-line goal>
**Outcome:** <done|partial|failed>
**Key Decisions:**
- <decision 1>
- <decision 2>
**Artifacts:** <list of files created, if any>
**Lessons:** <what worked, what didn't, what to do differently>
```

Keep the total entry under 400 words. Be factual, specific, and avoid padding.

---
{context}
---

Write only the Markdown entry, nothing else."""

        response = client.messages.create(
            model=_DISTILL_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def _plain_summary(self, mission: Dict, tasks: List[Dict]) -> str:
        """Structured plain-text fallback (no LLM)."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        done_tasks = [t for t in tasks if t.get("status") == "done"]
        failed_tasks = [t for t in tasks if t.get("status") == "failed"]
        outcome = "done" if not failed_tasks else ("partial" if done_tasks else "failed")

        lines = [
            f"### [{now}] Mission: {mission.get('title', 'Untitled')}",
            f"**Goal:** {mission.get('goal', '')}",
            f"**Outcome:** {outcome}",
            f"**Tasks completed:** {len(done_tasks)}/{len(tasks)}",
        ]

        # Include task outputs if present
        artifacts: List[str] = []
        notes: List[str] = []
        for task in done_tasks:
            details = task.get("details") or {}
            result = details.get("_exec_result") or {}
            summary = result.get("summary", "")
            if summary:
                notes.append(f"- [{task.get('agent_id')}] {task.get('title')}: {summary[:200]}")
            for art in result.get("artifacts") or []:
                if art.get("path"):
                    artifacts.append(art["path"])

        if artifacts:
            lines.append(f"**Artifacts:** {', '.join(artifacts[:10])}")
        if notes:
            lines += ["**Task Summaries:**"] + notes
        if failed_tasks:
            lines.append(f"**Failed:** {', '.join(t.get('title', '?') for t in failed_tasks)}")

        lines.append("")
        return "\n".join(lines)

    def _build_context(self, mission: Dict, tasks: List[Dict]) -> str:
        lines = [
            f"Mission ID: {mission.get('id')}",
            f"Title: {mission.get('title')}",
            f"Goal: {mission.get('goal')}",
            f"Mode: {mission.get('mode')}",
            f"Final status: {mission.get('status')}",
            "",
            "Tasks:",
        ]
        for task in tasks:
            details = task.get("details") or {}
            result = details.get("_exec_result") or {}
            summary = (result.get("summary") or "")[:_MAX_TASK_OUTPUT_CHARS]
            artifacts = [a.get("path", "") for a in (result.get("artifacts") or [])]
            lines += [
                f"  - [{task.get('status')}] {task.get('title')} (agent: {task.get('agent_id')})",
            ]
            if summary:
                lines.append(f"    Output: {summary}")
            if artifacts:
                lines.append(f"    Files: {', '.join(artifacts[:5])}")
        return "\n".join(lines)

    def _append_to_memory_file(self, entry: str) -> None:
        self._memory_file.parent.mkdir(parents=True, exist_ok=True)
        separator = "\n\n---\n\n"
        if self._memory_file.exists():
            with self._memory_file.open("a", encoding="utf-8") as f:
                f.write(separator + entry)
        else:
            self._memory_file.write_text(
                f"# Mission Memory Log\n\n{entry}", encoding="utf-8"
            )
