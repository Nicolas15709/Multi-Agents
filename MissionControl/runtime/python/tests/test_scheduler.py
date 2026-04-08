"""Tests for Scheduler module."""

import pytest
from unittest.mock import MagicMock

from runtime.python.scheduler import Scheduler, PRIORITY_SCORE, STATUS_SCORE
from runtime.python.models import Mission, Task


class TestScheduler:
    """Tests for Scheduler class."""

    @pytest.fixture
    def mission_repo(self):
        repo = MagicMock()
        return repo

    @pytest.fixture
    def task_repo(self):
        repo = MagicMock()
        return repo

    @pytest.fixture
    def scheduler(self, mission_repo, task_repo):
        return Scheduler(mission_repo, task_repo)

    def test_list_active_missions_filters_correctly(self, scheduler, mission_repo):
        mission_repo.list_missions.return_value = [
            {"id": "m1", "status": "queued", "priority": "high", "updated_at": "2025-01-01T00:00:00Z", "created_at": "2025-01-01T00:00:00Z"},
            {"id": "m2", "status": "running", "priority": "medium", "updated_at": "2025-01-01T00:00:00Z", "created_at": "2025-01-01T00:00:00Z"},
            {"id": "m3", "status": "completed", "priority": "low", "updated_at": "2025-01-01T00:00:00Z", "created_at": "2025-01-01T00:00:00Z"},
            {"id": "m4", "status": "blocked", "priority": "critical", "updated_at": "2025-01-01T00:00:00Z", "created_at": "2025-01-01T00:00:00Z"},
        ]
        active = scheduler.list_active_missions()
        assert len(active) == 3
        statuses = [m["status"] for m in active]
        assert "queued" in statuses
        assert "running" in statuses
        assert "blocked" in statuses
        assert "completed" not in statuses

    def test_highest_priority_mission_sorts_correctly(self, scheduler, mission_repo, task_repo):
        # Provide missions with various priorities and execution states
        missions = [
            {"id": "m1", "status": "queued", "priority": "low", "updated_at": "2025-01-01T00:00:00Z", "created_at": "2025-01-01T00:00:00Z"},
            {"id": "m2", "status": "queued", "priority": "critical", "updated_at": "2025-01-01T00:00:00Z", "created_at": "2025-01-01T00:00:00Z"},
            {"id": "m3", "status": "running", "priority": "medium", "updated_at": "2025-01-01T00:00:00Z", "created_at": "2025-01-01T00:00:00Z"},
        ]
        mission_repo.list_missions.return_value = missions
        # mission_execution_state returns "ready" for queued missions with ready tasks, "running" for those with running tasks, etc.
        # Here m1 -> idle (no tasks ready?), m2 -> ready (we'll simulate), m3 -> running
        def exec_state(mission_id):
            if mission_id == "m1":
                return "idle"
            if mission_id == "m2":
                return "ready"
            if mission_id == "m3":
                return "running"
            return "idle"
        scheduler.mission_execution_state = exec_state

        top = scheduler.highest_priority_mission()
        assert top is not None
        assert top["id"] == "m2"  # critical and ready gets top

    def test_should_interrupt(self, scheduler):
        assert scheduler.should_interrupt("low", "high") is True
        assert scheduler.should_interrupt("high", "low") is False
        assert scheduler.should_interrupt("medium", "medium") is False

    def test_resolve_conflict_decision(self, scheduler):
        # Higher priority interrupts
        decision = scheduler.resolve_conflict("low", "critical", "automatic")
        assert decision["decision"] == "interrupt"
        assert decision["reason"] == "incoming_higher_priority"

        # Manual request conflicts with important work
        decision = scheduler.resolve_conflict("high", "medium", "manual")
        assert decision["decision"] == "notify_user"
        assert decision["reason"] == "manual_request_conflicts_with_important_work"

        # Otherwise queue
        decision = scheduler.resolve_conflict("medium", "low", "automatic")
        assert decision["decision"] == "queue"
        assert decision["reason"] == "existing_work_keeps_priority"

    def test_pause_other_running_missions(self, scheduler, mission_repo):
        # Simulate running missions in DB
        mission_repo.db.fetchall.return_value = [
            {"id": "m_running1"},
            {"id": "m_running2"},
        ]
        # No state_updater so legacy path
        paused = scheduler.pause_other_running_missions("m_active")
        assert paused == ["m_running1", "m_running2"]
        # In legacy path, update_mission_status would be called twice
        assert mission_repo.update_mission_status.call_count == 2
