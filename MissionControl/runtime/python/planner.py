from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    from .mission_blueprints import build_mission_blueprint
    from .models import Mission, Task
    from .repository import MissionRepository, TaskRepository
    from .templates import TemplateRegistry
    from .thought_log import ThoughtLogService
    from .utils import new_id
except ImportError:  # pragma: no cover - runtime script compatibility
    from mission_blueprints import build_mission_blueprint
    from models import Mission, Task
    from repository import MissionRepository, TaskRepository
    from templates import TemplateRegistry
    from thought_log import ThoughtLogService
    from utils import new_id


@dataclass
class Planner:
    config: object
    mission_repository: MissionRepository
    task_repository: TaskRepository
    template_registry: Optional[TemplateRegistry] = None
    thought_log: Optional[ThoughtLogService] = None

    def create_mission(
        self,
        title: str,
        goal: str,
        mode: str,
        priority: str = "medium",
        source: str = "manual",
        allow_24x7: bool = False,
        schedule: Optional[str] = None,
    ) -> Mission:
        if self.thought_log:
            self.thought_log.record(
                "bootstrap",
                "create_mission",
                f"Planning mission '{title}'",
                {"mode": mode, "priority": priority, "source": source, "schedule": schedule},
            )
        mission = Mission(
            id=new_id("mission"),
            title=title,
            goal=goal,
            mode=mode,
            priority=priority,
            source=source,
            schedule=schedule,
            allow_24x7=allow_24x7,
        )
        self.mission_repository.create_mission(mission)
        self.mission_repository.add_event(
            mission.id,
            "mission_created",
            "system",
            f"Mission created: {title}",
            {
                "mode": mode,
                "priority": priority,
                "source": source,
                "schedule": schedule,
            },
        )
        return mission

    def _resolve_template(self, mode: str) -> Optional[Dict]:
        if not self.template_registry:
            return None
        try:
            return self.template_registry.get_template(mode)
        except KeyError:
            return None

    def _mission_payload(self, mission: Mission) -> Dict:
        return {
            "id": mission.id,
            "title": mission.title,
            "goal": mission.goal,
            "mode": mission.mode,
            "priority": mission.priority,
            "source": mission.source,
            "schedule": mission.schedule,
            "allow_24x7": mission.allow_24x7,
        }

    def _task_details_for_stage(
        self,
        *,
        mission: Mission,
        stages: List[Dict],
        index: int,
        stage: Dict,
        depends_on_task_ids: List[str],
        profile: Dict,
    ) -> Dict:
        next_agent = stages[index + 1]["owner_agent_id"] if index + 1 < len(stages) else None
        return {
            "mode": mission.mode,
            "workflow_version": profile.get("workflow_version", "open_capability_graph_v1"),
            "phase_kind": stage["phase_kind"],
            "phase_label": stage["phase_label"],
            "team_role": stage["team_role"],
            "sequence": index + 1,
            "sequence_total": len(stages),
            "owner_agent_id": stage["owner_agent_id"],
            "handoff": {
                "depends_on": list(depends_on_task_ids),
                "next_agent_id": next_agent,
            },
            "acceptance_criteria": list(stage.get("acceptance_criteria") or []),
            "guardrails": {
                "max_retries": int(stage.get("max_retries", 1) or 0),
                "escalate_on_failure": True,
                "prevent_infinite_retry": True,
            },
            "shared_memory_scope": "mission",
            "workstream": stage.get("workstream"),
            "required_capabilities": list(stage.get("required_capabilities") or []),
            "preferred_divisions": list(stage.get("preferred_divisions") or []),
            "specialist_template_hints": list(stage.get("specialist_template_hints") or []),
            "tool_primitives": list(stage.get("tool_primitives") or []),
            "approval_policy": stage.get("approval_policy") or "auto_allowed",
            "external_action_kind": stage.get("external_action_kind"),
            "coordination": {
                "shared_memory_scope": "mission",
                "handoff_style": "dependency_messages",
                "dependency_summaries_required": bool(depends_on_task_ids),
            },
            "mission_profile": {
                "domains": list(profile.get("domains") or []),
                "primary_domain": profile.get("primary_domain"),
                "intent_tags": list(profile.get("intent_tags") or []),
                "outcome_tags": list(profile.get("outcome_tags") or []),
                "risk_flags": list(profile.get("risk_flags") or []),
                "risk_level": profile.get("risk_level"),
                "requires_human_approval": bool(profile.get("requires_human_approval")),
                "preferred_divisions": list(profile.get("preferred_divisions") or []),
                "preferred_template_ids": list(profile.get("preferred_template_ids") or []),
            },
        }

    def seed_base_workflow(self, mission: Mission) -> List[Task]:
        template = self._resolve_template(mission.mode)
        blueprint = build_mission_blueprint(self._mission_payload(mission), template=template)
        stages = blueprint["stages"]
        profile = blueprint["profile"]

        stage_id_to_task_id: Dict[str, str] = {}
        tasks: List[Task] = []

        for index, stage in enumerate(stages):
            depends_on_task_ids = [
                stage_id_to_task_id[dependency_stage_id]
                for dependency_stage_id in stage.get("depends_on_stage_ids") or []
                if dependency_stage_id in stage_id_to_task_id
            ]
            task = Task(
                id=new_id("task"),
                mission_id=mission.id,
                agent_id=stage["owner_agent_id"],
                title=stage["title"],
                priority=mission.priority,
                depends_on=depends_on_task_ids,
                details=self._task_details_for_stage(
                    mission=mission,
                    stages=stages,
                    index=index,
                    stage=stage,
                    depends_on_task_ids=depends_on_task_ids,
                    profile=profile,
                ),
            )
            self.task_repository.create_task(task)
            tasks.append(task)
            stage_id_to_task_id[stage["id"]] = task.id

        self.mission_repository.add_event(
            mission.id,
            "workflow_seeded",
            "planner",
            "Open capability workflow seeded",
            {
                "tasks": [task.id for task in tasks],
                "mode": mission.mode,
                "agents": [task.agent_id for task in tasks],
                "workflow_version": profile.get("workflow_version", "open_capability_graph_v1"),
                "phases": [task.details.get("phase_kind") for task in tasks],
                "plan": {
                    "domains": profile.get("domains"),
                    "intent_tags": profile.get("intent_tags"),
                    "outcome_tags": profile.get("outcome_tags"),
                    "risk_flags": profile.get("risk_flags"),
                    "risk_level": profile.get("risk_level"),
                    "preferred_divisions": profile.get("preferred_divisions"),
                    "preferred_template_ids": profile.get("preferred_template_ids"),
                    "requires_human_approval": profile.get("requires_human_approval"),
                    "parallel_tracks": profile.get("recommended_parallel_tracks"),
                },
            },
        )
        if self.thought_log:
            self.thought_log.record(
                mission.id,
                "seed_open_workflow",
                "Dynamic capability graph seeded for mission",
                {
                    "workflow_length": len(tasks),
                    "agents": [task.agent_id for task in tasks],
                    "phases": [task.details.get("phase_kind") for task in tasks],
                    "domains": profile.get("domains"),
                    "intent_tags": profile.get("intent_tags"),
                    "risk_level": profile.get("risk_level"),
                },
            )
        return tasks

    def summary(self) -> dict:
        return {
            "agenda": "advanced",
            "status": "open-capability-graph",
            "supports": [
                "backlog",
                "priorities",
                "scheduled_tasks",
                "cooldowns",
                "future_planning",
                "conflict_resolution",
                "dynamic_blueprints",
                "open_capability_graphs",
                "team_lead_closeout",
                "task_guardrails",
                "risk_gated_closeout",
            ],
            "missions": len(self.mission_repository.list_missions()),
        }
