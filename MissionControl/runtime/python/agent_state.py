"""Agent state management with transactional updates."""

from typing import Dict, Optional

try:
    from .repository import AgentRepository
    from .state_machine import AgentStateMachine, TransactionalStateUpdater, StateValidationError
except ImportError:  # pragma: no cover - runtime script compatibility
    from repository import AgentRepository
    from state_machine import AgentStateMachine, TransactionalStateUpdater, StateValidationError


class AgentStateManager:
    def __init__(self, repository: AgentRepository, state_updater: Optional[TransactionalStateUpdater] = None):
        self.repository = repository
        self.state_updater = state_updater
        self._agents_cache = None

    def _ensure_agents_cache(self):
        if self._agents_cache is None:
            self._agents_cache = {agent["agent_id"]: agent for agent in self.repository.list_agents()}

    def set_state(self, agent_id: str, state: str, mission_id: str = None, task_id: str = None, validate: bool = True, reason: Optional[str] = None, actor: Optional[str] = None) -> None:
        self._ensure_agents_cache()

        # Validate transition if state_updater is available
        if self.state_updater and validate:
            agent = self._agents_cache.get(agent_id)
            if agent:
                from_state = agent["state"]
                if from_state == state:
                    return
                if not AgentStateMachine.can_transition(from_state, state):
                    raise StateValidationError(
                        f"Invalid agent state transition: {agent_id} {from_state} -> {state}"
                    )
            # If agent doesn't exist, we allow the creation with any state

        # Determine agent metadata (existing or defaults)
        if agent_id in self._agents_cache:
            agent_meta = self._agents_cache[agent_id]
        else:
            # Fetch from DB to get metadata if not in cache
            agent_record = self.repository.get_agent(agent_id)
            if agent_record:
                agent_meta = agent_record
                self._agents_cache[agent_id] = agent_meta
            else:
                agent_meta = {
                    "display_name": agent_id,
                    "role": "unknown",
                    "personality": None,
                    "reports_to": None,
                    "capabilities": [],
                    "budget_monthly_cents": 0,
                    "origin": "runtime",
                    "mission_scope_id": mission_id,
                    "metadata": {},
                    "state": state,  # initial state
                }

        # Use transactional updater if available for atomic update + history
        if self.state_updater:
            # Direct upsert; state_updater manages history separately (full ACID integration pending)
            self.repository.upsert_agent(
                type("AgentProxy", (), {
                    "agent_id": agent_id,
                    "display_name": agent_meta["display_name"],
                    "role": agent_meta["role"],
                    "state": state,
                    "active_mission_id": mission_id,
                    "current_task_id": task_id,
                    "personality": agent_meta.get("personality"),
                    "reports_to": agent_meta.get("reports_to"),
                    "capabilities": agent_meta.get("capabilities") or [],
                    "budget_monthly_cents": agent_meta.get("budget_monthly_cents") or 0,
                    "origin": agent_meta.get("origin") or "runtime",
                    "mission_scope_id": agent_meta.get("mission_scope_id"),
                    "metadata": agent_meta.get("metadata") or {},
                })()
            )
            # TODO: Integrate agent state transitions into state_updater transaction for full ACID
        else:
            # Legacy direct upsert
            self.repository.upsert_agent(
                type("AgentProxy", (), {
                    "agent_id": agent_id,
                    "display_name": agent_meta["display_name"],
                    "role": agent_meta["role"],
                    "state": state,
                    "active_mission_id": mission_id,
                    "current_task_id": task_id,
                    "personality": agent_meta.get("personality"),
                    "reports_to": agent_meta.get("reports_to"),
                    "capabilities": agent_meta.get("capabilities") or [],
                    "budget_monthly_cents": agent_meta.get("budget_monthly_cents") or 0,
                    "origin": agent_meta.get("origin") or "runtime",
                    "mission_scope_id": agent_meta.get("mission_scope_id"),
                    "metadata": agent_meta.get("metadata") or {},
                })()
            )

        # Update cache
        self._agents_cache[agent_id] = {
            "agent_id": agent_id,
            "display_name": agent_meta["display_name"],
            "role": agent_meta["role"],
            "state": state,
            "active_mission_id": mission_id,
            "current_task_id": task_id,
            "personality": agent_meta.get("personality"),
            "reports_to": agent_meta.get("reports_to"),
            "capabilities": agent_meta.get("capabilities") or [],
            "budget_monthly_cents": agent_meta.get("budget_monthly_cents") or 0,
            "origin": agent_meta.get("origin") or "runtime",
            "mission_scope_id": agent_meta.get("mission_scope_id"),
            "metadata": agent_meta.get("metadata") or {},
        }

    def summary(self) -> Dict:
        items = self.repository.list_agents()
        self._agents_cache = {item["agent_id"]: item for item in items}
        return {
            "count": len(items),
            "states": {item["agent_id"]: item["state"] for item in items},
        }
