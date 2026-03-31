"""Tests for State Machine module."""

import pytest

from runtime.python.state_machine import (
    MissionStateMachine,
    TaskStateMachine,
    AgentStateMachine,
    StateTransition,
    StateHistory,
    StateValidationError,
    TransactionalStateUpdater,
    StateReconciler,
)
from runtime.python.models import Mission, Task
from runtime.python.repository import MissionRepository, TaskRepository, AgentRepository


class TestMissionStateMachine:
    """Tests for MissionStateMachine."""

    def test_valid_transitions(self):
        """Test all defined valid transitions."""
        valid = MissionStateMachine.VALID_TRANSITIONS
        assert "queued" in valid
        assert "running" in valid
        assert "blocked" in valid
        assert "needs_human" in valid
        assert "completed" in valid

    def test_can_transition(self):
        """Test transition validation."""
        assert MissionStateMachine.can_transition("queued", "running") is True
        assert MissionStateMachine.can_transition("queued", "blocked") is True
        assert MissionStateMachine.can_transition("queued", "completed") is True
        assert MissionStateMachine.can_transition("queued", "needs_human") is True
        assert MissionStateMachine.can_transition("queued", "idle") is False

        assert MissionStateMachine.can_transition("running", "queued") is True
        assert MissionStateMachine.can_transition("running", "blocked") is True
        assert MissionStateMachine.can_transition("running", "needs_human") is True
        assert MissionStateMachine.can_transition("running", "completed") is True
        assert MissionStateMachine.can_transition("running", "idle") is False

        assert MissionStateMachine.can_transition("blocked", "queued") is True
        assert MissionStateMachine.can_transition("blocked", "running") is True
        assert MissionStateMachine.can_transition("blocked", "needs_human") is True
        assert MissionStateMachine.can_transition("blocked", "completed") is False

        assert MissionStateMachine.can_transition("needs_human", "queued") is True
        assert MissionStateMachine.can_transition("needs_human", "running") is True
        assert MissionStateMachine.can_transition("needs_human", "completed") is True

        assert MissionStateMachine.can_transition("completed", "queued") is False

    def test_is_terminal(self):
        """Test terminal state detection."""
        assert MissionStateMachine.is_terminal("completed") is True
        assert MissionStateMachine.is_terminal("queued") is False
        assert MissionStateMachine.is_terminal("running") is False
        assert MissionStateMachine.is_terminal("blocked") is False
        assert MissionStateMachine.is_terminal("needs_human") is False

    def test_get_allowed_transitions(self):
        """Test getting allowed next states."""
        assert set(MissionStateMachine.get_allowed_transitions("queued")) == {"running", "blocked", "needs_human", "completed"}
        assert set(MissionStateMachine.get_allowed_transitions("running")) == {"queued", "blocked", "needs_human", "completed"}
        assert MissionStateMachine.get_allowed_transitions("completed") == []

    def test_validate_unknown_state(self):
        """Test validation with unknown states."""
        assert MissionStateMachine.can_transition("unknown", "running") is False
        assert MissionStateMachine.can_transition("queued", "unknown") is False


class TestTaskStateMachine:
    """Tests for TaskStateMachine."""

    def test_valid_transitions(self):
        """Test all defined valid transitions."""
        valid = TaskStateMachine.VALID_TRANSITIONS
        assert "pending" in valid
        assert "running" in valid
        assert "blocked" in valid
        assert "failed" in valid
        assert "done" in valid

    def test_can_transition(self):
        """Test transition validation."""
        assert TaskStateMachine.can_transition("pending", "running") is True
        assert TaskStateMachine.can_transition("pending", "blocked") is True
        assert TaskStateMachine.can_transition("pending", "failed") is True
        assert TaskStateMachine.can_transition("pending", "done") is False

        assert TaskStateMachine.can_transition("running", "done") is True
        assert TaskStateMachine.can_transition("running", "failed") is True
        assert TaskStateMachine.can_transition("running", "blocked") is True
        assert TaskStateMachine.can_transition("running", "pending") is False

        assert TaskStateMachine.can_transition("blocked", "pending") is True
        assert TaskStateMachine.can_transition("blocked", "failed") is True
        assert TaskStateMachine.can_transition("blocked", "running") is False

        assert TaskStateMachine.can_transition("failed", "pending") is True
        assert TaskStateMachine.can_transition("failed", "running") is False

        assert TaskStateMachine.can_transition("done", "pending") is False

    def test_is_terminal(self):
        """Test terminal state detection."""
        assert TaskStateMachine.is_terminal("done") is True
        assert TaskStateMachine.is_terminal("pending") is False
        assert TaskStateMachine.is_terminal("running") is False
        assert TaskStateMachine.is_terminal("blocked") is False
        assert TaskStateMachine.is_terminal("failed") is False


class TestAgentStateMachine:
    """Tests for AgentStateMachine."""

    def test_valid_transitions(self):
        """Test all defined valid transitions."""
        valid = AgentStateMachine.VALID_TRANSITIONS
        assert "idle" in valid
        assert "planning" in valid
        assert "researching" in valid
        assert "designing" in valid
        assert "building" in valid
        assert "reviewing" in valid
        assert "blocked" in valid

    def test_can_transition(self):
        """Test transition validation."""
        # From idle to any working state
        assert AgentStateMachine.can_transition("idle", "planning") is True
        assert AgentStateMachine.can_transition("idle", "researching") is True
        assert AgentStateMachine.can_transition("idle", "designing") is True
        assert AgentStateMachine.can_transition("idle", "building") is True
        assert AgentStateMachine.can_transition("idle", "reviewing") is True
        assert AgentStateMachine.can_transition("idle", "blocked") is True

        # From working states to idle or blocked
        assert AgentStateMachine.can_transition("planning", "idle") is True
        assert AgentStateMachine.can_transition("planning", "blocked") is True
        assert AgentStateMachine.can_transition("planning", "researching") is False

        assert AgentStateMachine.can_transition("researching", "idle") is True
        assert AgentStateMachine.can_transition("researching", "blocked") is True

        assert AgentStateMachine.can_transition("blocked", "idle") is True
        assert AgentStateMachine.can_transition("blocked", "planning") is False

    def test_is_terminal(self):
        """Test that agents have no terminal states."""
        assert AgentStateMachine.is_terminal("idle") is False
        assert AgentStateMachine.is_terminal("planning") is False
        assert AgentStateMachine.is_terminal("blocked") is False


class TestStateHistory:
    """Tests for StateHistory."""

    def test_record_and_retrieve(self):
        """Test recording and retrieving transitions."""
        history = StateHistory()
        t1 = StateTransition("mission", "m1", "queued", "running")
        t2 = StateTransition("mission", "m1", "running", "completed")
        t3 = StateTransition("task", "t1", "pending", "running")

        history.record(t1)
        history.record(t2)
        history.record(t3)

        # Get mission history
        mission_history = history.get_history("m1", "mission")
        assert len(mission_history) == 2
        assert mission_history[0].to_status == "running"
        assert mission_history[1].to_status == "completed"

        # Get task history
        task_history = history.get_history("t1", "task")
        assert len(task_history) == 1

        # Get all history for entity (should also work)
        all_m1 = history.get_history("m1")
        assert len(all_m1) == 2

    def test_get_latest(self):
        """Test getting latest transition."""
        history = StateHistory()
        t1 = StateTransition("mission", "m1", "queued", "running", timestamp="2024-01-01T00:00:00Z")
        t2 = StateTransition("mission", "m1", "running", "completed", timestamp="2024-01-01T01:00:00Z")
        history.record(t1)
        history.record(t2)

        latest = history.get_latest("m1", "mission")
        assert latest is not None
        assert latest.to_status == "completed"

        # Non-existent entity
        latest = history.get_latest("nonexistent", "mission")
        assert latest is None


class TestTransactionalStateUpdater:
    """Tests for TransactionalStateUpdater."""

    def test_transaction_commit(self, database):
        """Test committing a transaction."""
        repo = MissionRepository(database)
        history = StateHistory()
        updater = TransactionalStateUpdater(repo, None, history)

        # Create a test mission
        mission_id = "test-mission"
        from runtime.python.models import Mission
        mission = Mission(
            id=mission_id,
            title="Test",
            goal="Test goal",
            mode="test",
            priority="medium",
            status="queued",
        )
        repo.create_mission(mission)

        # Perform transition in transaction
        updater.begin_transaction()
        updater.transition_mission(mission_id, "running", reason="test", actor="tester")
        updater.commit_transaction()

        # Verify state change
        mission = repo.get_mission(mission_id)
        assert mission["status"] == "running"

        # Verify history
        transitions = history.get_history(mission_id, "mission")
        assert len(transitions) == 1
        assert transitions[0].to_status == "running"
        assert transitions[0].reason == "test"

    def test_transaction_rollback(self, database):
        """Test rolling back a transaction."""
        repo = MissionRepository(database)
        history = StateHistory()
        updater = TransactionalStateUpdater(repo, None, history)

        mission_id = "test-mission"
        from runtime.python.models import Mission
        mission = Mission(
            id=mission_id,
            title="Test",
            goal="Test goal",
            mode="test",
            priority="medium",
            status="queued",
        )
        repo.create_mission(mission)

        # Begin transaction and perform transition
        updater.begin_transaction()
        updater.transition_mission(mission_id, "running", reason="test", actor="tester")
        # Rollback before commit
        updater.rollback_transaction()

        # Verify state unchanged
        mission = repo.get_mission(mission_id)
        assert mission["status"] == "queued"

        # Verify no history recorded
        transitions = history.get_history(mission_id, "mission")
        assert len(transitions) == 0

    def test_invalid_transition_raises(self, database):
        """Test that invalid transitions raise error."""
        repo = MissionRepository(database)
        history = StateHistory()
        updater = TransactionalStateUpdater(repo, None, history)

        mission_id = "test-mission"
        from runtime.python.models import Mission
        mission = Mission(
            id=mission_id,
            title="Test",
            goal="Test goal",
            mode="test",
            priority="medium",
            status="queued",
        )
        repo.create_mission(mission)

        updater.begin_transaction()
        with pytest.raises(StateValidationError, match="Invalid mission state transition"):
            updater.transition_mission(mission_id, "invalid_status")
        updater.rollback_transaction()


class TestStateReconciler:
    """Tests for StateReconciler."""

    def test_reconcile_mission_completed(self, database):
        """Test reconciliation marks mission completed when all tasks done."""
        from runtime.python.models import Mission, Task

        mission_repo = MissionRepository(database)
        task_repo = TaskRepository(database)
        history = StateHistory()
        updater = TransactionalStateUpdater(mission_repo, task_repo, history)
        reconciler = StateReconciler(mission_repo, task_repo, updater)

        # Create mission with queued status
        mission_id = "test-mission"
        mission = Mission(
            id=mission_id,
            title="Test",
            goal="Test",
            mode="test",
            priority="medium",
            status="queued",
        )
        mission_repo.create_mission(mission)

        # Create completed tasks
        task1 = Task(
            id="task-1",
            mission_id=mission_id,
            agent_id="agent-0",
            title="Task 1",
            status="done",
            priority="medium",
            depends_on=[],
        )
        task2 = Task(
            id="task-2",
            mission_id=mission_id,
            agent_id="agent-1",
            title="Task 2",
            status="completed",
            priority="medium",
            depends_on=[],
        )
        task_repo.create_task(task1)
        task_repo.create_task(task2)

        # Reconcile without applying
        result = reconciler.reconcile_mission_states(apply=False)
        assert result["inconsistencies_found"] == 1
        assert result["fixes_applied"] == 0

        # Reconcile with applying
        result = reconciler.reconcile_mission_states(apply=True)
        assert result["inconsistencies_found"] == 1
        assert result["fixes_applied"] == 1
        assert result["details"][0]["to"] == "completed"

        # Verify state changed
        mission = mission_repo.get_mission(mission_id)
        assert mission["status"] == "completed"

    def test_reconcile_mission_running(self, database):
        """Test reconciliation ensures running mission has running tasks."""
        from runtime.python.models import Mission, Task

        mission_repo = MissionRepository(database)
        task_repo = TaskRepository(database)
        history = StateHistory()
        updater = TransactionalStateUpdater(mission_repo, task_repo, history)
        reconciler = StateReconciler(mission_repo, task_repo, updater)

        mission_id = "test-mission"
        mission = Mission(
            id=mission_id,
            title="Test",
            goal="Test",
            mode="test",
            priority="medium",
            status="running",
        )
        mission_repo.create_mission(mission)

        # Create pending tasks (inconsistency: mission running but no tasks running)
        task1 = Task(
            id="task-1",
            mission_id=mission_id,
            agent_id="agent-0",
            title="Task 1",
            status="pending",
            priority="medium",
            depends_on=[],
        )
        task_repo.create_task(task1)

        result = reconciler.reconcile_mission_states(apply=True)
        # Mission should be changed to queued (or blocked) since it's inconsistent
        mission = mission_repo.get_mission(mission_id)
        # After reconciliation, status should be queued since there are pending tasks but none running
        assert mission["status"] in ["queued", "blocked"]
