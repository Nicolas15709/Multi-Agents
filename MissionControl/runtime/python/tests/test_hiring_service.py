from pathlib import Path

from runtime.python.hiring_service import HiringService
import pytest

from runtime.python.models import Mission, MissionControlRecord, Task
from runtime.python.specialist_templates import SpecialistTemplateCatalog
from runtime.python.templates import TemplateRegistry


def seed_base_mission(mission_repository, task_repository):
    mission = Mission(
        id="mission-hire",
        title="Hire specialists",
        goal="Need extra specialists for a mission",
        mode="feature_extension",
        priority="high",
    )
    mission_repository.create_mission(mission)
    kickoff = Task(
        id="task-kickoff",
        mission_id=mission.id,
        agent_id="agent-0",
        title="Lead kickoff",
        details={"phase_kind": "lead_plan"},
    )
    review = Task(
        id="task-review",
        mission_id=mission.id,
        agent_id="agent-4",
        title="Review output",
        depends_on=["task-kickoff"],
        details={"phase_kind": "review", "handoff": {"depends_on": ["task-kickoff"]}},
    )
    closeout = Task(
        id="task-closeout",
        mission_id=mission.id,
        agent_id="agent-0",
        title="Close mission",
        depends_on=["task-review"],
        details={"phase_kind": "lead_closeout", "handoff": {"depends_on": ["task-review"]}},
    )
    task_repository.create_task(kickoff)
    task_repository.create_task(review)
    task_repository.create_task(closeout)
    return mission


def test_hire_subagent_creates_agent_and_task(
    mission_repository,
    task_repository,
    agent_repository,
    agent_hire_request_repository,
):
    mission = seed_base_mission(mission_repository, task_repository)
    service = HiringService(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_repository=agent_repository,
        hire_request_repository=agent_hire_request_repository,
    )

    result = service.hire_subagent(
        mission_id=mission.id,
        display_name="API Fixer",
        role="backend-specialist",
        personality="Sharp on APIs and auth bugs",
        capabilities=["fastapi", "debugging", "tests"],
        notes="Focus on payment API edge cases",
    )

    agent = agent_repository.get_agent(result["agent_id"])
    task = task_repository.get_task(result["task_id"])
    review = task_repository.get_task("task-review")
    closeout = task_repository.get_task("task-closeout")
    hire_requests = agent_hire_request_repository.list_requests_for_mission(mission.id)

    assert agent["display_name"] == "API Fixer"
    assert agent["origin"] == "mission_hire"
    assert agent["mission_scope_id"] == mission.id
    assert agent["capabilities"] == ["fastapi", "debugging", "tests"]
    assert task["agent_id"] == result["agent_id"]
    assert task["details"]["phase_kind"] == "specialist_hire"
    assert result["task_id"] in review["depends_on"]
    assert result["task_id"] in closeout["depends_on"]
    assert hire_requests[0]["hired_agent_id"] == result["agent_id"]


def test_hiring_service_can_request_approval_only(
    mission_repository,
    task_repository,
    agent_repository,
    agent_hire_request_repository,
):
    mission = seed_base_mission(mission_repository, task_repository)
    service = HiringService(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_repository=agent_repository,
        hire_request_repository=agent_hire_request_repository,
        approvals_enabled=True,
    )

    result = service.hire_subagent(
        mission_id=mission.id,
        display_name="Security Reviewer",
        role="security-specialist",
        capabilities=["security", "auth"],
    )

    requests = agent_hire_request_repository.list_requests_for_mission(mission.id)

    assert result["status"] == "pending"
    assert result["agent_id"] is None
    assert requests[0]["status"] == "pending"


def test_hiring_service_suggests_specialists_from_mission_context(
    mission_repository,
    task_repository,
    agent_repository,
    agent_hire_request_repository,
):
    mission = Mission(
        id="mission-suggest",
        title="Fix auth API and mobile dashboard bugs",
        goal="Stabilize backend auth flow and responsive dashboard.",
        mode="bugfix_debug",
        priority="high",
    )
    mission_repository.create_mission(mission)
    service = HiringService(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_repository=agent_repository,
        hire_request_repository=agent_hire_request_repository,
    )

    suggestions = service.suggest_subagents_for_mission(mission.id)
    roles = {item["role"] for item in suggestions}

    assert "frontend-specialist" in roles
    assert "backend-specialist" in roles


def test_hiring_service_blocks_approval_when_dynamic_hire_budget_is_exhausted(
    mission_repository,
    task_repository,
    agent_repository,
    agent_hire_request_repository,
    mission_control_repository,
):
    mission = seed_base_mission(mission_repository, task_repository)
    mission_control_repository.create_control(
        MissionControlRecord(
            mission_id=mission.id,
            max_dynamic_hires=1,
            dynamic_hires_used=1,
        )
    )
    service = HiringService(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_repository=agent_repository,
        hire_request_repository=agent_hire_request_repository,
        mission_control_repository=mission_control_repository,
    )

    request = service.request_subagent(
        mission_id=mission.id,
        display_name="Overflow Specialist",
        role="frontend-specialist",
        capabilities=["react"],
    )

    with pytest.raises(ValueError, match="dynamic hire budget exhausted"):
        service.approve_hire_request(request["hire_request_id"])


def test_hiring_service_can_seed_pending_requests_from_mission_context(
    mission_repository,
    task_repository,
    agent_repository,
    agent_hire_request_repository,
):
    mission = Mission(
        id="mission-seed",
        title="Harden auth API and dashboard UX",
        goal="Need backend reliability and frontend polish before shipping.",
        mode="feature_extension",
        priority="high",
    )
    mission_repository.create_mission(mission)
    service = HiringService(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_repository=agent_repository,
        hire_request_repository=agent_hire_request_repository,
    )

    result = service.seed_suggested_requests_for_mission(mission.id)
    requests = agent_hire_request_repository.list_requests_for_mission(mission.id)
    roles = {item["role"] for item in requests}

    assert result["created"] >= 2
    assert "frontend-specialist" in roles
    assert "backend-specialist" in roles
    assert all(item["status"] == "pending" for item in requests)


def test_hiring_service_uses_agency_catalog_for_marketing_missions(
    mission_repository,
    task_repository,
    agent_repository,
    agent_hire_request_repository,
):
    mission = Mission(
        id="mission-marketing",
        title="Launch a social media marketing push",
        goal="Need content, campaign strategy, and social growth for the launch.",
        mode="marketing_campaign",
        priority="high",
    )
    mission_repository.create_mission(mission)

    root = Path(__file__).resolve().parent.parent.parent.parent.parent / "references" / "agency-agents"
    service = HiringService(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_repository=agent_repository,
        hire_request_repository=agent_hire_request_repository,
        template_registry=TemplateRegistry(str(Path(__file__).resolve().parent.parent.parent.parent / "config" / "mission-templates.json")),
        specialist_template_catalog=SpecialistTemplateCatalog(str(root)),
    )

    suggestions = service.suggest_subagents_for_mission(mission.id)
    suggestion_ids = {item.get("template_id") for item in suggestions}

    assert "marketing-growth-hacker" in suggestion_ids
    assert "marketing-social-media-strategist" in suggestion_ids


def test_hiring_service_surfaces_capability_gaps_from_task_plan(
    mission_repository,
    task_repository,
    agent_repository,
    agent_hire_request_repository,
):
    mission = Mission(
        id="mission-gap",
        title="Need SEO and outbound followup",
        goal="Build a proposal and outbound sequence with SEO landing support.",
        mode="general_operating_request",
        priority="high",
    )
    mission_repository.create_mission(mission)
    task_repository.create_task(
        Task(
            id="task-gap",
            mission_id=mission.id,
            agent_id="agent-0",
            title="Gap planning",
            details={
                "phase_kind": "strategy",
                "required_capabilities": ["seo", "outreach", "positioning"],
                "preferred_divisions": ["marketing", "sales"],
                "workstream": "strategy",
            },
        )
    )

    root = Path(__file__).resolve().parent.parent.parent.parent.parent / "references" / "agency-agents"
    service = HiringService(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_repository=agent_repository,
        hire_request_repository=agent_hire_request_repository,
        template_registry=TemplateRegistry(str(Path(__file__).resolve().parent.parent.parent.parent / "config" / "mission-templates.json")),
        specialist_template_catalog=SpecialistTemplateCatalog(str(root)),
    )

    suggestions = service.suggest_subagents_for_mission(mission.id)

    assert suggestions
    assert any(item.get("gap_capabilities") for item in suggestions)
