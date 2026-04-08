from runtime.python.models import Mission
from runtime.python.planner import Planner
from runtime.python.templates import TemplateRegistry


def build_planner(mission_repository, task_repository, mock_config):
    return Planner(
        config=mock_config,
        mission_repository=mission_repository,
        task_repository=task_repository,
        template_registry=TemplateRegistry(mock_config.templates_path),
    )


def test_seed_base_workflow_builds_open_capability_graph_for_general_mission(mission_repository, task_repository, mock_config):
    planner = build_planner(mission_repository, task_repository, mock_config)
    mission = Mission(
        id="mission-general-open",
        title="Launch a new local business growth system",
        goal="Research the market, design an offer, build a demo website, create outreach assets, and review before contacting leads.",
        mode="general_operating_request",
        priority="high",
        status="queued",
    )
    mission_repository.create_mission(mission)

    tasks = planner.seed_base_workflow(mission)
    phases = [task.details["phase_kind"] for task in tasks]
    workstreams = [task.details.get("workstream") for task in tasks]
    build_tasks = [task for task in tasks if task.details["phase_kind"] == "build"]

    assert phases[0] == "lead_plan"
    assert "research" in phases
    assert "strategy" in phases
    assert "build" in phases
    assert "outreach" in phases
    assert phases[-1] == "lead_closeout"
    assert tasks[-1].depends_on == [tasks[-2].id]
    assert tasks[0].details["workflow_version"] == "open_capability_graph_v1"
    assert tasks[0].details["mission_profile"]["requires_human_approval"] is True
    assert "external-action" in workstreams
    assert len(build_tasks) >= 2
    assert any(task.details.get("tool_primitives") for task in tasks)
    assert any(task.details.get("approval_policy") == "per_action_approval" for task in tasks)
    assert any(task.details.get("external_action_kind") == "outreach" for task in tasks)


def test_seed_base_workflow_research_only_skips_delivery_but_keeps_review_and_closeout(mission_repository, task_repository, mock_config):
    planner = build_planner(mission_repository, task_repository, mock_config)
    mission = Mission(
        id="mission-research-open",
        title="Research competitor pricing",
        goal="Investigate competitors, analyze positioning, and return a concise decision memo.",
        mode="research_only",
        priority="medium",
        status="queued",
    )
    mission_repository.create_mission(mission)

    tasks = planner.seed_base_workflow(mission)
    phases = [task.details["phase_kind"] for task in tasks]

    assert phases == ["lead_plan", "research", "documentation", "review", "lead_closeout"]
    assert tasks[-1].depends_on == [tasks[-2].id]
    assert tasks[1].details["workstream"] == "discovery"
    assert tasks[2].details["workstream"] == "documentation"
    assert tasks[2].details["tool_primitives"]
