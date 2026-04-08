from unittest.mock import MagicMock

from runtime.python.approval_service import ActionApprovalService
from runtime.python.coordination_service import CoordinationService
from runtime.python.models import Mission, MissionControlRecord, Task
from runtime.python.repository import ActionApprovalRepository, AgentMessageRepository, MissionMemoryRepository
from runtime.python.task_runner import TaskRunner


def test_failed_task_is_retried_when_guardrail_allows(database, mission_repository, task_repository, mission_control_repository):
    mission = Mission(
        id="mission-retry",
        title="Retry mission",
        goal="Avoid infinite loops but allow one controlled retry",
        mode="software_build",
        priority="medium",
        status="running",
    )
    mission_repository.create_mission(mission)
    mission_control_repository.create_control(MissionControlRecord(mission_id=mission.id))

    task = Task(
        id="task-retry",
        mission_id=mission.id,
        agent_id="agent-3",
        title="Implement the approved solution",
        status="failed",
        priority="medium",
        depends_on=[],
        details={
            "phase_kind": "build",
            "guardrails": {
                "max_retries": 1,
            },
            "retry_count": 0,
        },
    )
    task_repository.create_task(task)

    agent_state_manager = MagicMock()
    progress_notifier = MagicMock()
    runner = TaskRunner(
        mission_repository=mission_repository,
        task_repository=task_repository,
        mission_control_repository=mission_control_repository,
        agent_state_manager=agent_state_manager,
        progress_notifier=progress_notifier,
        state_updater=None,
    )

    result = runner.advance_next_task(mission.id)
    updated_task = task_repository.get_task(task.id)
    updated_mission = mission_repository.get_mission(mission.id)

    assert result["status"] == "retry_scheduled"
    assert updated_task["status"] == "pending"
    assert updated_task["details"]["retry_count"] == 1
    assert updated_mission["status"] == "queued"
    agent_state_manager.set_state.assert_called_with("agent-3", "idle")


def test_failed_task_escalates_after_retry_budget_exhausted(database, mission_repository, task_repository, mission_control_repository):
    mission = Mission(
        id="mission-escalate",
        title="Escalate mission",
        goal="Stop retrying once retry budget is exhausted",
        mode="software_build",
        priority="high",
        status="running",
    )
    mission_repository.create_mission(mission)
    mission_control_repository.create_control(MissionControlRecord(mission_id=mission.id))

    task = Task(
        id="task-escalate",
        mission_id=mission.id,
        agent_id="agent-4",
        title="Validate, harden, and review the delivery",
        status="failed",
        priority="high",
        depends_on=[],
        details={
            "phase_kind": "review",
            "guardrails": {
                "max_retries": 1,
            },
            "retry_count": 1,
        },
    )
    task_repository.create_task(task)

    agent_state_manager = MagicMock()
    progress_notifier = MagicMock()
    runner = TaskRunner(
        mission_repository=mission_repository,
        task_repository=task_repository,
        mission_control_repository=mission_control_repository,
        agent_state_manager=agent_state_manager,
        progress_notifier=progress_notifier,
        state_updater=None,
    )

    result = runner.advance_next_task(mission.id)
    updated_mission = mission_repository.get_mission(mission.id)

    assert result["status"] == "needs_human"
    assert updated_mission["status"] == "needs_human"
    agent_state_manager.set_state.assert_called_with(
        "agent-4",
        "blocked",
        mission_id=mission.id,
        task_id=task.id,
    )


def test_task_runner_halts_when_estimated_token_budget_is_exhausted(
    database,
    mission_repository,
    task_repository,
    mission_control_repository,
):
    mission = Mission(
        id="mission-budget",
        title="Budgeted mission",
        goal="Avoid wasting tokens on runaway autonomy",
        mode="software_build",
        priority="high",
        status="queued",
    )
    mission_repository.create_mission(mission)
    mission_control_repository.create_control(
        MissionControlRecord(
            mission_id=mission.id,
            max_autonomous_steps=5,
            max_estimated_tokens=1000,
            max_runtime_ticks=10,
        )
    )
    task = Task(
        id="task-build",
        mission_id=mission.id,
        agent_id="agent-3",
        title="Implement the approved solution",
        status="pending",
        priority="high",
        depends_on=[],
        details={"phase_kind": "build"},
    )
    task_repository.create_task(task)

    agent_state_manager = MagicMock()
    progress_notifier = MagicMock()
    runner = TaskRunner(
        mission_repository=mission_repository,
        task_repository=task_repository,
        mission_control_repository=mission_control_repository,
        agent_state_manager=agent_state_manager,
        progress_notifier=progress_notifier,
        state_updater=None,
    )

    result = runner.advance_next_task(mission.id)
    updated_mission = mission_repository.get_mission(mission.id)
    control = mission_control_repository.get_control(mission.id)

    assert result["status"] == "budget_exhausted"
    assert result["reason"] == "estimated_token_budget_exhausted"
    assert updated_mission["status"] == "needs_human"
    assert control["status"] == "exhausted"


def test_task_runner_requests_approval_for_external_action(database, mission_repository, task_repository, mission_control_repository):
    mission = Mission(
        id="mission-approval",
        title="Outreach mission",
        goal="Prepare and send outreach only after approval",
        mode="general_operating_request",
        priority="high",
        status="queued",
    )
    mission_repository.create_mission(mission)
    mission_control_repository.create_control(
        MissionControlRecord(
            mission_id=mission.id,
            action_budgets={"outreach": 2},
        )
    )
    task = Task(
        id="task-outreach",
        mission_id=mission.id,
        agent_id="agent-3",
        title="Prepare outreach pack",
        status="pending",
        priority="high",
        depends_on=[],
        details={
            "phase_kind": "outreach",
            "approval_policy": "per_action_approval",
            "external_action_kind": "outreach",
            "tool_primitives": ["crm", "email", "approval-gate"],
        },
    )
    task_repository.create_task(task)

    approval_repository = ActionApprovalRepository(database)
    runner = TaskRunner(
        mission_repository=mission_repository,
        task_repository=task_repository,
        mission_control_repository=mission_control_repository,
        agent_state_manager=MagicMock(),
        progress_notifier=MagicMock(),
        state_updater=None,
        approval_service=ActionApprovalService(
            repository=approval_repository,
            mission_repository=mission_repository,
        ),
    )

    result = runner.advance_next_task(mission.id)
    approvals = approval_repository.list_for_mission(mission.id)

    assert result["status"] == "awaiting_approval"
    assert len(approvals) == 1
    assert approvals[0]["action_kind"] == "outreach"
    assert mission_repository.get_mission(mission.id)["status"] == "needs_human"


def test_task_runner_records_shared_memory_handoff_on_completion(database, mission_repository, task_repository, mission_control_repository):
    mission = Mission(
        id="mission-handoff",
        title="Shared memory mission",
        goal="Complete one task and hand it off to the reviewer",
        mode="software_build",
        priority="medium",
        status="running",
    )
    mission_repository.create_mission(mission)
    mission_control_repository.create_control(MissionControlRecord(mission_id=mission.id))
    running = Task(
        id="task-running",
        mission_id=mission.id,
        agent_id="agent-3",
        title="Implement solution",
        status="running",
        priority="medium",
        depends_on=[],
        details={"phase_kind": "build", "workstream": "engineering", "required_capabilities": ["engineering", "delivery"]},
    )
    dependent = Task(
        id="task-dependent",
        mission_id=mission.id,
        agent_id="agent-4",
        title="Review solution",
        status="pending",
        priority="medium",
        depends_on=["task-running"],
        details={"phase_kind": "review", "workstream": "review", "required_capabilities": ["review"]},
    )
    task_repository.create_task(running)
    task_repository.create_task(dependent)

    coordination = CoordinationService(
        task_repository=task_repository,
        memory_repository=MissionMemoryRepository(database),
        message_repository=AgentMessageRepository(database),
    )
    runner = TaskRunner(
        mission_repository=mission_repository,
        task_repository=task_repository,
        mission_control_repository=mission_control_repository,
        agent_state_manager=MagicMock(),
        progress_notifier=MagicMock(),
        state_updater=None,
        coordination_service=coordination,
    )

    runner.advance_next_task(mission.id)
    memory = MissionMemoryRepository(database).list_recent(mission.id)
    messages = AgentMessageRepository(database).list_messages_for_mission(mission.id)

    assert memory
    assert messages
    assert messages[0]["target_task_id"] == "task-dependent"
