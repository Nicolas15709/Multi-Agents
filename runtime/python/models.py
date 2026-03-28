from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


Priority = Literal["low", "medium", "high", "critical"]
MissionStatus = Literal["queued", "running", "blocked", "completed", "needs_human"]
TaskStatus = Literal["pending", "running", "done", "blocked", "failed"]
AgentState = Literal["idle", "planning", "researching", "designing", "building", "reviewing", "blocked"]


class Mission(BaseModel):
    id: str
    title: str
    goal: str
    mode: str
    priority: Priority = "medium"
    status: MissionStatus = "queued"
    source: Literal["manual", "scheduled", "system"] = "manual"
    schedule: Optional[str] = None
    allow_24x7: bool = False


class Task(BaseModel):
    id: str
    mission_id: str
    agent_id: str
    title: str
    status: TaskStatus = "pending"
    priority: Priority = "medium"
    depends_on: List[str] = Field(default_factory=list)
    details: Dict = Field(default_factory=dict)


class AgentRecord(BaseModel):
    agent_id: str
    display_name: str
    role: str
    state: AgentState = "idle"
    active_mission_id: Optional[str] = None
    current_task_id: Optional[str] = None
    personality: Optional[str] = None


class PolicyRecord(BaseModel):
    id: str
    integration: str
    account_resource: str
    action: str
    mode: Literal["forbidden", "auto_allowed", "conditional", "per_action_approval"]
    conditions: Dict = Field(default_factory=dict)
    enabled: bool = True


class NotificationRecord(BaseModel):
    channel: str
    kind: str
    status: str
    summary: str
    payload: Dict = Field(default_factory=dict)
