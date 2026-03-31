"""Tests for TaskRepository."""

import uuid

import pytest

from runtime.python.models import Task
from runtime.python.repository import TaskRepository


def create_test_task(
    task_id=None,
    mission_id=None,
    agent_id="agent-1",
    title="Test Task",
    status="pending",  # allowed: pending, running, done, blocked, failed
    priority="medium",
    depends_on=None,
    details=None,
):
    """Helper to create a test task."""
    return Task(
        id=task_id or str(uuid.uuid4()),
        mission_id=mission_id or str(uuid.uuid4()),
        agent_id=agent_id,
        title=title,
        status=status,
        priority=priority,
        depends_on=depends_on or [],
        details=details or {},
    )


def test_create_task(task_repository):
    """Test creating a task."""
    task = create_test_task()
    task_repository.create_task(task)

    # Tasks are retrieved via list_tasks_for_mission
    tasks = task_repository.list_tasks_for_mission(task.mission_id)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Test Task"
    assert tasks[0]["status"] == "queued"


def test_list_tasks_for_mission(task_repository):
    """Test listing tasks for a mission."""
    mission_id = str(uuid.uuid4())

    task1 = create_test_task(mission_id=mission_id, title="Task 1", priority="high")
    task2 = create_test_task(mission_id=mission_id, title="Task 2", priority="low")
    task3 = create_test_task(mission_id=mission_id, title="Task 3", priority="medium")

    task_repository.create_task(task1)
    task_repository.create_task(task2)
    task_repository.create_task(task3)

    tasks = task_repository.list_tasks_for_mission(mission_id)
    assert len(tasks) == 3
    # Should be ordered by created_at ASC
    titles = [t["title"] for t in tasks]
    assert titles == ["Task 1", "Task 2", "Task 3"]


def test_update_task_status(task_repository):
    """Test updating task status."""
    task = create_test_task()
    task_repository.create_task(task)

    task_repository.update_task_status(task.id, "running")
    tasks = task_repository.list_tasks_for_mission(task.mission_id)
    updated_task = tasks[0]
    assert updated_task["status"] == "running"


def test_task_depends_on_deserialization(task_repository):
    """Test that depends_on field is properly deserialized."""
    task = create_test_task(depends_on=["task-1", "task-2"])
    task_repository.create_task(task)

    tasks = task_repository.list_tasks_for_mission(task.mission_id)
    retrieved = tasks[0]
    assert isinstance(retrieved["depends_on"], list)
    assert retrieved["depends_on"] == ["task-1", "task-2"]


def test_task_details_deserialization(task_repository):
    """Test that details field is properly deserialized."""
    task = create_test_task(details={"step": 1, "notes": "test"})
    task_repository.create_task(task)

    tasks = task_repository.list_tasks_for_mission(task.mission_id)
    retrieved = tasks[0]
    assert isinstance(retrieved["details"], dict)
    assert retrieved["details"] == {"step": 1, "notes": "test"}
