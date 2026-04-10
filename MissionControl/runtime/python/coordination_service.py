from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

try:
    from .models import AgentMessageRecord, MissionMemoryRecord
    from .repository import AgentMessageRepository, MissionMemoryRepository, TaskRepository
    from .utils import dedupe as _dedupe
except ImportError:  # pragma: no cover - runtime script compatibility
    from models import AgentMessageRecord, MissionMemoryRecord
    from repository import AgentMessageRepository, MissionMemoryRepository, TaskRepository
    from utils import dedupe as _dedupe


@dataclass
class CoordinationService:
    task_repository: TaskRepository
    memory_repository: MissionMemoryRepository
    message_repository: AgentMessageRepository

    def _task_summary(self, task: Dict) -> Dict:
        details = task.get("details") or {}
        return {
            "task_id": task["id"],
            "title": task.get("title"),
            "agent_id": task.get("agent_id"),
            "phase_kind": details.get("phase_kind"),
            "phase_label": details.get("phase_label"),
            "workstream": details.get("workstream"),
            "required_capabilities": list(details.get("required_capabilities") or []),
            "tool_primitives": list(details.get("tool_primitives") or []),
            "risk_flags": list((details.get("mission_profile") or {}).get("risk_flags") or []),
            "approval_policy": details.get("approval_policy"),
            "external_action_kind": details.get("external_action_kind"),
        }

    def record_completion_handoffs(self, mission_id: str, task: Dict, all_tasks: List[Dict]) -> None:
        details = task.get("details") or {}
        workstream = details.get("workstream") or details.get("phase_kind") or "delivery"
        memory_key = f"{workstream}:{task['id']}"
        summary = f"{task.get('title')} completed for workstream {workstream}"
        payload = self._task_summary(task)

        self.memory_repository.create_entry(
            MissionMemoryRecord(
                mission_id=mission_id,
                source_task_id=task["id"],
                author_agent_id=task.get("agent_id"),
                scope="mission",
                memory_key=memory_key,
                summary=summary,
                content=payload,
            )
        )

        dependents = [candidate for candidate in all_tasks if task["id"] in (candidate.get("depends_on") or [])]
        for dependent in dependents:
            self.message_repository.create_message(
                AgentMessageRecord(
                    mission_id=mission_id,
                    from_agent_id=task.get("agent_id"),
                    to_agent_id=dependent.get("agent_id"),
                    source_task_id=task["id"],
                    target_task_id=dependent["id"],
                    kind="handoff",
                    summary=summary,
                    payload={
                        "completed_task": payload,
                        "target_task_id": dependent["id"],
                        "target_title": dependent.get("title"),
                    },
                )
            )

    def attach_context_to_task(self, mission_id: str, task: Dict) -> Dict:
        details = dict(task.get("details") or {})
        consumed_messages = self.message_repository.consume_for_task(
            mission_id,
            task.get("agent_id"),
            task.get("id"),
        )
        recent_memory = self.memory_repository.list_recent(mission_id, limit=8)

        details["coordination_context"] = {
            "recent_handoffs": [
                {
                    "id": message.get("id"),
                    "from_agent_id": message.get("from_agent_id"),
                    "summary": message.get("summary"),
                    "payload": message.get("payload") or {},
                }
                for message in consumed_messages
            ],
            "shared_memory": [
                {
                    "id": entry.get("id"),
                    "summary": entry.get("summary"),
                    "content": entry.get("content") or {},
                }
                for entry in recent_memory
            ],
            "required_capabilities": _dedupe(details.get("required_capabilities") or []),
            "tool_primitives": _dedupe(details.get("tool_primitives") or []),
        }
        self.task_repository.update_task_details(task["id"], details)
        return details["coordination_context"]
