"""Tests for MissionRepository."""

import uuid
from datetime import datetime, timezone

import pytest

from runtime.python.models import Mission
from runtime.python.repository import MissionRepository
from runtime.python.utils import utc_now


def create_test_mission(
    mission_id=None,
    title="Test Mission",
    goal="Test goal",
    mode="test_mode",
    priority="medium",
    status="queued",
    source="manual",  # allowed: manual, scheduled, system
    allow_24x7=False,
):
    """Helper to create a test mission."""
    return Mission(
        id=mission_id or str(uuid.uuid4()),
        title=title,
        goal=goal,
        mode=mode,
        priority=priority,
        status=status,
        source=source,
        schedule=None,
        allow_24x7=allow_24x7,
    )


def test_create_mission(mission_repository):
    """Test creating a mission."""
    mission = create_test_mission()
    mission_repository.create_mission(mission)

    retrieved = mission_repository.get_mission(mission.id)
    assert retrieved is not None
    assert retrieved["title"] == "Test Mission"
    assert retrieved["goal"] == "Test goal"
    assert retrieved["status"] == "queued"


def test_list_missions(mission_repository):
    """Test listing missions."""
    # Create multiple missions
    mission1 = create_test_mission(title="Mission 1")
    mission2 = create_test_mission(title="Mission 2")
    mission3 = create_test_mission(title="Mission 3")

    mission_repository.create_mission(mission1)
    mission_repository.create_mission(mission2)
    mission_repository.create_mission(mission3)

    missions = mission_repository.list_missions()
    assert len(missions) == 3
    # Should be ordered by created_at DESC
    titles = [m["title"] for m in missions]
    assert titles.index("Mission 3") < titles.index("Mission 2") < titles.index("Mission 1")


def test_list_active_missions(mission_repository):
    """Test listing only active missions."""
    mission1 = create_test_mission(title="Active 1", status="running")
    mission2 = create_test_mission(title="Active 2", status="queued")
    mission3 = create_test_mission(title="Inactive", status="completed")

    mission_repository.create_mission(mission1)
    mission_repository.create_mission(mission2)
    mission_repository.create_mission(mission3)

    active = mission_repository.list_active_missions()
    assert len(active) == 2
    statuses = {m["status"] for m in active}
    assert statuses == {"running", "queued"}


def test_get_focus_mission(mission_repository):
    """Test getting the focus mission based on priority and status."""
    # Create missions with different priorities and statuses
    mission_low_queued = create_test_mission(
        title="Low Queued", priority="low", status="queued"
    )
    mission_high_running = create_test_mission(
        title="High Running", priority="high", status="running"
    )
    mission_medium_blocked = create_test_mission(
        title="Medium Blocked", priority="medium", status="blocked"
    )
    mission_critical_queued = create_test_mission(
        title="Critical Queued", priority="critical", status="queued"
    )

    for m in [mission_low_queued, mission_high_running, mission_medium_blocked, mission_critical_queued]:
        mission_repository.create_mission(m)

    focus = mission_repository.get_focus_mission()
    # Focus should be the running mission with highest status score (running=3)
    assert focus["title"] == "High Running"

    # If we pause the running mission, focus should change
    mission_repository.update_mission_status(mission_high_running.id, "paused")

    focus = mission_repository.get_focus_mission()
    # Now the critical queued should be focus (highest priority among non-running)
    assert focus["title"] == "Critical Queued"


def test_update_mission_status(mission_repository):
    """Test updating mission status."""
    mission = create_test_mission()
    mission_repository.create_mission(mission)

    mission_repository.update_mission_status(mission.id, "running")
    updated = mission_repository.get_mission(mission.id)
    assert updated["status"] == "running"


def test_add_event(mission_repository):
    """Test adding an event to a mission."""
    mission = create_test_mission()
    mission_repository.create_mission(mission)

    mission_repository.add_event(
        mission_id=mission.id,
        event_type="agent_assigned",
        actor="supervisor",
        summary="Agent assigned to mission",
        payload={"agent_id": "agent-1"},
    )

    events = mission_repository.recent_events(mission_id=mission.id, limit=1)
    assert len(events) == 1
    assert events[0]["event_type"] == "agent_assigned"
    assert events[0]["actor"] == "supervisor"
    assert events[0]["payload"]["agent_id"] == "agent-1"


def test_recent_events(mission_repository):
    """Test retrieving recent events."""
    mission = create_test_mission()
    mission_repository.create_mission(mission)

    # Add multiple events
    for i in range(5):
        mission_repository.add_event(
            mission_id=mission.id,
            event_type=f"event_{i}",
            actor="test",
            summary=f"Event {i}",
        )

    events = mission_repository.recent_events(mission_id=mission.id, limit=3)
    assert len(events) == 3
    # Should be in reverse chronological order (newest first)
    event_types = [e["event_type"] for e in events]
    assert event_types == ["event_4", "event_3", "event_2"]
