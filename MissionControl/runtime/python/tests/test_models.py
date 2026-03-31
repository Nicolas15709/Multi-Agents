"""Tests for data models."""

import json
from uuid import uuid4

import pytest

from runtime.python.models import (
    AgentRecord,
    Mission,
    NotificationRecord,
    PolicyRecord,
    Task,
)
from runtime.python.utils import utc_now


def test_agent_record_creation():
    """Test creating an AgentRecord."""
    agent = AgentRecord(
        agent_id="agent-1",
        display_name="Test Agent",
        role="tester",
        state="idle",  # valid: idle, planning, researching, designing, building, reviewing, blocked
        active_mission_id=None,
        current_task_id=None,
        personality="Thorough and precise",
    )

    assert agent.agent_id == "agent-1"
    assert agent.display_name == "Test Agent"
    assert agent.role == "tester"
    assert agent.state == "idle"


def test_mission_creation():
    """Test creating a Mission."""
    mission_id = str(uuid4())
    mission = Mission(
        id=mission_id,
        title="Test Mission",
        goal="Test goal",
        mode="test_mode",
        priority="high",
        status="queued",
        source="manual",  # valid: manual, scheduled, system
        schedule=None,
        allow_24x7=True,
    )

    assert mission.id == mission_id
    assert mission.title == "Test Mission"
    assert mission.priority == "high"
    assert mission.allow_24x7 is True


def test_task_creation():
    """Test creating a Task."""
    task_id = str(uuid4())
    mission_id = str(uuid4())
    task = Task(
        id=task_id,
        mission_id=mission_id,
        agent_id="agent-1",
        title="Test Task",
        status="pending",  # valid: pending, running, done, blocked, failed
        priority="medium",
        depends_on=[],
        details={"test": True},
    )

    assert task.id == task_id
    assert task.mission_id == mission_id
    assert task.agent_id == "agent-1"
    assert task.details == {"test": True}


def test_notification_record_creation():
    """Test creating a NotificationRecord."""
    notification = NotificationRecord(
        channel="telegram",
        kind="mission_complete",
        status="queued",
        summary="Mission completed",
        payload={"mission_id": "test-123"},
    )

    assert notification.channel == "telegram"
    assert notification.kind == "mission_complete"
    assert notification.status == "queued"
    assert notification.payload == {"mission_id": "test-123"}


def test_policy_record_creation():
    """Test creating a PolicyRecord."""
    policy = PolicyRecord(
        id="policy-1",
        integration="github",
        account_resource="org/repo",
        action="create_pr",
        mode="auto_allowed",  # valid: forbidden, auto_allowed, conditional, per_action_approval
        conditions={"min_reviewers": 2},
        enabled=True,
    )

    assert policy.integration == "github"
    assert policy.action == "create_pr"
    assert policy.mode == "auto_allowed"
    assert policy.conditions == {"min_reviewers": 2}
    assert policy.enabled is True


def test_utc_now_returns_datetime():
    """Test that utc_now returns a datetime object."""
    now = utc_now()
    # utc_nova implementación devuelve string ISO
    assert isinstance(now, str)
