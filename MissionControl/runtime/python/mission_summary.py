from dataclasses import dataclass

try:
    from .repository import MissionRepository, TaskRepository
except ImportError:  # pragma: no cover - runtime script compatibility
    from repository import MissionRepository, TaskRepository


@dataclass
class MissionSummaryService:
    mission_repository: MissionRepository
    task_repository: TaskRepository

    def build(self, mission_id: str):
        mission = self.mission_repository.get_mission(mission_id)
        if not mission:
            return None
        tasks = self.task_repository.list_tasks_for_mission(mission_id)
        mission_profile = next(
            (task.get("details", {}).get("mission_profile") for task in tasks if task.get("details", {}).get("mission_profile")),
            {},
        ) or {}
        workflow_version = next(
            (task.get("details", {}).get("workflow_version") for task in tasks if task.get("details", {}).get("workflow_version")),
            None,
        )
        workstreams = []
        required_capabilities = []
        specialist_template_hints = []
        tool_primitives = []
        approval_policies = []
        external_action_kinds = []
        for task in tasks:
            details = task.get("details") or {}
            workstream = details.get("workstream")
            if workstream and workstream not in workstreams:
                workstreams.append(workstream)
            for capability in details.get("required_capabilities") or []:
                if capability not in required_capabilities:
                    required_capabilities.append(capability)
            for template_id in details.get("specialist_template_hints") or []:
                if template_id not in specialist_template_hints:
                    specialist_template_hints.append(template_id)
            for tool in details.get("tool_primitives") or []:
                if tool not in tool_primitives:
                    tool_primitives.append(tool)
            if details.get("approval_policy") and details.get("approval_policy") not in approval_policies:
                approval_policies.append(details.get("approval_policy"))
            if details.get("external_action_kind") and details.get("external_action_kind") not in external_action_kinds:
                external_action_kinds.append(details.get("external_action_kind"))
        return {
            "mission": {
                "id": mission["id"],
                "title": mission["title"],
                "goal": mission["goal"],
                "mode": mission["mode"],
                "priority": mission["priority"],
                "status": mission["status"],
                "source": mission["source"],
            },
            "tasks": [
                {
                    "id": task["id"],
                    "agent_id": task["agent_id"],
                    "title": task["title"],
                    "status": task["status"],
                    "priority": task["priority"],
                }
                for task in tasks
            ],
            "plan": {
                "workflow_version": workflow_version,
                "domains": mission_profile.get("domains") or [],
                "primary_domain": mission_profile.get("primary_domain"),
                "intent_tags": mission_profile.get("intent_tags") or [],
                "outcome_tags": mission_profile.get("outcome_tags") or [],
                "risk_flags": mission_profile.get("risk_flags") or [],
                "risk_level": mission_profile.get("risk_level"),
                "requires_human_approval": bool(mission_profile.get("requires_human_approval")),
                "preferred_divisions": mission_profile.get("preferred_divisions") or [],
                "preferred_template_ids": mission_profile.get("preferred_template_ids") or [],
                "workstreams": workstreams,
                "required_capabilities": required_capabilities,
                "specialist_template_hints": specialist_template_hints,
                "tool_primitives": tool_primitives,
                "approval_policies": approval_policies,
                "external_action_kinds": external_action_kinds,
            },
            "counts": {
                "total": len(tasks),
                "done": sum(1 for task in tasks if task["status"] == "done"),
                "running": sum(1 for task in tasks if task["status"] == "running"),
                "pending": sum(1 for task in tasks if task["status"] == "pending"),
                "blocked": sum(1 for task in tasks if task["status"] == "blocked"),
                "failed": sum(1 for task in tasks if task["status"] == "failed"),
            },
        }
