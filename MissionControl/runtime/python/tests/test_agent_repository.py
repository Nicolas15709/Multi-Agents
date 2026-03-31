"""Tests for AgentRepository."""

import uuid

import pytest

from runtime.python.models import AgentRecord
from runtime.python.repository import AgentRepository


def create_test_agent(
    agent_id=None,
    display_name="Test Agent",
    role="tester",
    state="idle",  # allowed: idle, planning, researching, designing, building, reviewing, blocked
    active_mission_id=None,
    current_task_id=None,
    personality="Test personality",
):
    """Helper to create a test agent."""
    return AgentRecord(
        agent_id=agent_id or str(uuid.uuid4()),
        display_name=display_name,
        role=role,
        state=state,
        active_mission_id=active_mission_id,
        current_task_id=current_task_id,
        personality=personality,
    )


def test_upsert_agent_creates_new(agent_repository):
    """Test upserting a new agent creates it."""
    agent = create_test_agent()
    agent_repository.upsert_agent(agent)

    agents = agent_repository.list_agents()
    assert len(agents) == 1
    assert agents[0]["agent_id"] == agent.agent_id
    assert agents[0]["display_name"] == "Test Agent"


def test_upsert_agent_updates_existing(agent_repository):
    """Test upserting an existing agent updates it."""
    agent_id = "existing-agent"
    agent1 = create_test_agent(
        agent_id=agent_id,
        display_name="Original Name",
        role="original_role",
    )
    agent2 = create_test_agent(
        agent_id=agent_id,
        display_name="Updated Name",
        role="updated_role",
        state="blocked",  # Valid state
    )

    agent_repository.upsert_agent(agent1)
    agent_repository.upsert_agent(agent2)

    agents = agent_repository.list_agents()
    assert len(agents) == 1
    assert agents[0]["display_name"] == "Updated Name"
    assert agents[0]["role"] == "updated_role"
    assert agents[0]["state"] == "blocked"


def test_list_agents_ordered(agent_repository):
    """Test that agents are listed in order."""
    agent1 = create_test_agent(agent_id="agent-a", display_name="Agent A")
    agent2 = create_test_agent(agent_id="agent-b", display_name="Agent B")
    agent3 = create_test_agent(agent_id="agent-c", display_name="Agent C")

    agent_repository.upsert_agent(agent3)
    agent_repository.upsert_agent(agent1)
    agent_repository.upsert_agent(agent2)

    agents = agent_repository.list_agents()
    agent_ids = [a["agent_id"] for a in agents]
    assert agent_ids == ["agent-a", "agent-b", "agent-c"]
