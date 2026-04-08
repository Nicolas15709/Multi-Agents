from unittest.mock import MagicMock

from runtime.python.intake_service import IntakeService
from runtime.python.notifications import NotificationService


def build_service(mock_config, intake_request_repository, mission_repository, notification_repository):
    mission_service = MagicMock()
    mission_service.submit_mission.return_value = {
        "mission_id": "mission-from-intake",
        "status": "queued",
    }
    notifications = NotificationService(config=mock_config, repository=notification_repository)
    agent_state_manager = MagicMock()
    service = IntakeService(
        intake_repository=intake_request_repository,
        mission_repository=mission_repository,
        mission_service=mission_service,
        notifications=notifications,
        agent_state_manager=agent_state_manager,
    )
    return service, mission_service, agent_state_manager


def test_submit_problem_auto_dispatches_to_mission(
    mock_config,
    intake_request_repository,
    mission_repository,
    notification_repository,
):
    service, mission_service, agent_state_manager = build_service(
        mock_config,
        intake_request_repository,
        mission_repository,
        notification_repository,
    )

    result = service.submit_problem(
        title="Login roto",
        description="Usuarios no pueden iniciar sesión desde iPhone.",
        priority="high",
        channel="openclaw",
        source="openclaw",
        auto_dispatch=True,
    )

    request = intake_request_repository.get_request(result["request"]["id"])

    assert result["ok"] is True
    assert result["duplicate"] is False
    assert result["mission_id"] == "mission-from-intake"
    assert request["status"] == "dispatched"
    assert request["mission_id"] == "mission-from-intake"
    mission_service.submit_mission.assert_called_once()
    agent_state_manager.set_state.assert_called_with("agent-0", "planning", mission_id="mission-from-intake")
    assert request["details"]["inferred_profile"]["domains"]


def test_submit_problem_deduplicates_active_request(
    mock_config,
    intake_request_repository,
    mission_repository,
    notification_repository,
):
    service, mission_service, _agent_state_manager = build_service(
        mock_config,
        intake_request_repository,
        mission_repository,
        notification_repository,
    )

    first = service.submit_problem(
        title="Checkout roto",
        description="El botón de pago falla con error 500.",
        auto_dispatch=True,
    )
    second = service.submit_problem(
        title="Checkout roto",
        description="El botón de pago falla con error 500.",
        auto_dispatch=True,
    )

    requests = intake_request_repository.list_requests()

    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert second["mission_id"] == "mission-from-intake"
    assert len(requests) == 1
    mission_service.submit_mission.assert_called_once()


def test_submit_problem_defaults_to_general_operating_request_for_open_ended_work(
    mock_config,
    intake_request_repository,
    mission_repository,
    notification_repository,
):
    service, mission_service, _agent_state_manager = build_service(
        mock_config,
        intake_request_repository,
        mission_repository,
        notification_repository,
    )

    result = service.submit_problem(
        title="Need help with a new agency workflow",
        description="Figure out the best strategy, create the assets, and prepare next actions for the client.",
        auto_dispatch=False,
    )

    request = intake_request_repository.get_request(result["request"]["id"])

    assert result["duplicate"] is False
    assert request["mode"] == "general_operating_request"
    assert request["details"]["inferred_profile"]["domains"]
    mission_service.submit_mission.assert_not_called()
