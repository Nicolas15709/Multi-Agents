from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


Priority = Literal["low", "medium", "high", "critical"]
MissionStatus = Literal["queued", "running", "blocked", "completed", "needs_human"]
TaskStatus = Literal["pending", "running", "done", "completed", "blocked", "failed"]
AgentState = Literal["idle", "planning", "researching", "designing", "building", "reviewing", "blocked"]
MissionSource = Literal["manual", "scheduled", "system", "api", "mobile", "openclaw"]
IntakeRequestStatus = Literal["pending", "dispatched", "duplicate", "resolved", "rejected"]


class Mission(BaseModel):
    id: str
    title: str
    goal: str
    mode: str
    priority: Priority = "medium"
    status: MissionStatus = "queued"
    source: MissionSource = "manual"
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
    reports_to: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    budget_monthly_cents: int = 0
    origin: str = "core"
    mission_scope_id: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)


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


class IntakeRequestRecord(BaseModel):
    id: str
    title: str
    description: str
    status: IntakeRequestStatus = "pending"
    priority: Priority = "medium"
    requested_by: Optional[str] = None
    channel: str = "mobile"
    source: MissionSource = "mobile"
    mode: Optional[str] = None
    fingerprint: Optional[str] = None
    mission_id: Optional[str] = None
    details: Dict = Field(default_factory=dict)


class AgentHireRequestRecord(BaseModel):
    id: str
    mission_id: str
    requested_by_agent_id: Optional[str] = None
    display_name: str
    role: str
    personality: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    budget_monthly_cents: int = 0
    reports_to: Optional[str] = None
    notes: Optional[str] = None
    status: Literal["pending", "approved", "rejected", "hired"] = "pending"
    hired_agent_id: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)


class MissionControlRecord(BaseModel):
    mission_id: str
    max_autonomous_steps: int = 18
    autonomous_steps_used: int = 0
    max_estimated_tokens: int = 16000
    estimated_tokens_used: int = 0
    max_runtime_ticks: int = 64
    runtime_ticks_used: int = 0
    max_dynamic_hires: int = 3
    dynamic_hires_used: int = 0
    action_budgets: Dict = Field(default_factory=dict)
    action_usage: Dict = Field(default_factory=dict)
    status: Literal["active", "paused", "exhausted"] = "active"
    notes: Optional[str] = None


class MissionMemoryRecord(BaseModel):
    mission_id: str
    source_task_id: Optional[str] = None
    author_agent_id: Optional[str] = None
    scope: str = "mission"
    memory_key: Optional[str] = None
    summary: str
    content: Dict = Field(default_factory=dict)


class AgentMessageRecord(BaseModel):
    mission_id: str
    from_agent_id: Optional[str] = None
    to_agent_id: Optional[str] = None
    source_task_id: Optional[str] = None
    target_task_id: Optional[str] = None
    kind: str = "handoff"
    status: Literal["queued", "delivered", "consumed"] = "queued"
    summary: str
    payload: Dict = Field(default_factory=dict)


class ActionApprovalRecord(BaseModel):
    id: str
    mission_id: str
    task_id: str
    requested_by_agent_id: Optional[str] = None
    action_kind: str
    policy_mode: str = "per_action_approval"
    status: Literal["pending", "approved", "rejected"] = "pending"
    reason: Optional[str] = None
    approved_by: Optional[str] = None
    decision_notes: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)
