"""Tests for Startup Recovery Service."""

import pytest
from unittest.mock import MagicMock, patch

from runtime.python.startup_recovery import StartupRecoveryService
from runtime.python.state_machine import TransactionalStateUpdater, StateReconciler


class TestStartupRecoveryService:
    """Tests for StartupRecoveryService."""

    @pytest.fixture
    def mission_repository(self):
        repo = MagicMock()
        return repo

    @pytest.fixture
    def task_repository(self):
        repo = MagicMock()
        return repo

    @pytest.fixture
    def agent_state_manager(self):
        manager = MagicMock()
        return manager

    @pytest.fixture
    def scheduler(self):
        sched = MagicMock()
        return sched

    @pytest.fixture
    def state_updater(self):
        updater = MagicMock(spec=TransactionalStateUpdater)
        return updater

    @pytest.fixture
    def state_reconciler(self):
        reconciler = MagicMock(spec=StateReconciler)
        return reconciler

    @pytest.fixture
    def recovery_service(self, mission_repository, task_repository, agent_state_manager, scheduler, state_updater, state_reconciler):
        return StartupRecoveryService(
            mission_repository=mission_repository,
            task_repository=task_repository,
            agent_state_manager=agent_state_manager,
            scheduler=scheduler,
            state_updater=state_updater,
            state_reconciler=state_reconciler,
        )

    def test_inspect_calls_recover_with_apply_false(self, recovery_service):
        # Setup mission list
        recovery_service.mission_repository.list_missions.return_value = [{"id": "m1", "status": "queued"}]
        recovery_service.scheduler.highest_priority_mission.return_value = {"id": "m1"}
        result = recovery_service.inspect()
        assert result["status"] in ("noop", "needs_recovery", "recovered")
        # Because apply=False, status should be "needs_recovery" if updates exist, else "noop"
        # In this minimal setup, no inconsistencies, so "noop"
        assert result["status"] == "noop"

    def test_recover_applies_changes(self, recovery_service):
        recovery_service.mission_repository.list_missions.return_value = [{"id": "m1", "status": "queued"}]
        recovery_service.scheduler.highest_priority_mission.return_value = {"id": "m1"}
        # Reconciler returns a fix
        recovery_service.state_reconciler.reconcile_mission_states.return_value = {
            "inconsistencies_found": 1,
            "fixes_applied": 1,
            "details": [{"mission_id": "m1", "from": "running", "to": "queued"}],
        }
        # No running tasks to reset
        recovery_service.task_repository.list_tasks_for_mission.return_value = []

        result = recovery_service.recover()
        assert result["status"] == "recovered"
        assert result["counts"]["missions_requeued"] == 1
        # Should have called reconciler with apply=True
        recovery_service.state_reconciler.reconcile_mission_states.assert_called_once_with(apply=True)

    def test_recovery_handles_stale_running_tasks(self, recovery_service):
        # Mission with a running task that should be reset
        mission = {"id": "m1", "status": "running"}
        tasks = [
            {"id": "t1", "status": "running", "agent_id": "agent-1"},
        ]
        recovery_service.mission_repository.list_missions.return_value = [mission]
        recovery_service.scheduler.highest_priority_mission.return_value = mission
        recovery_service.task_repository.list_tasks_for_mission.return_value = tasks
        recovery_service.state_reconciler.reconcile_mission_states.return_value = {"fixes_applied": 0, "details": []}

        result = recovery_service.recover()
        assert result["counts"]["tasks_reset"] == 1
        assert result["counts"]["agents_reset"] == 1
        # Agent state manager should be reset to idle
        recovery_service.agent_state_manager.set_state.assert_called_once_with("agent-1", "idle")
        # Task status should be updated to pending (via state_updater if available, else direct)
        if recovery_service.state_updater:
            recovery_service.state_updater.begin_transaction.assert_called()
            recovery_service.state_updater.transition_task.assert_called()
            recovery_service.state_updater.commit_transaction.assert_called()
        else:
            recovery_service.task_repository.update_task_status.assert_called_with("t1", "pending")

    def test_focus_mission_normalization_on_invalid_status(self, recovery_service):
        mission = {"id": "m1", "status": "unknown"}
        tasks = []
        recovery_service.mission_repository.list_missions.return_value = [mission]
        recovery_service.scheduler.highest_priority_mission.return_value = mission
        recovery_service.task_repository.list_tasks_for_mission.return_value = tasks
        recovery_service.state_reconciler.reconcile_mission_states.return_value = {"fixes_applied": 0, "details": []}

        result = recovery_service.recover()
        # It should attempt to transition mission to "queued"
        if recovery_service.state_updater:
            recovery_service.state_updater.transition_task.assert_not_called()
            recovery_service.state_updater.transition_mission.assert_called_with(
                "m1", "queued", reason="normalize_focus_mission", actor="startup_recovery"
            )
        assert result["counts"]["missions_requeued"] == 1

    def test_no_missions_early_exit(self, recovery_service):
        recovery_service.mission_repository.list_missions.return_value = []
        result = recovery_service._recover(apply=True)
        assert result["status"] == "no_missions"
        assert result["focus_mission_id"] is None
