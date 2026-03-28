from typing import Dict

from repository import AgentRepository


class AgentStateManager:
    def __init__(self, repository: AgentRepository):
        self.repository = repository

    def set_state(self, agent_id: str, state: str, mission_id: str = None, task_id: str = None) -> None:
        agents = {agent["agent_id"]: agent for agent in self.repository.list_agents()}
        agent = agents[agent_id]
        self.repository.upsert_agent(
            type("AgentProxy", (), {
                "agent_id": agent_id,
                "display_name": agent["display_name"],
                "role": agent["role"],
                "state": state,
                "active_mission_id": mission_id,
                "current_task_id": task_id,
                "personality": agent.get("personality"),
            })()
        )

    def summary(self) -> Dict:
        items = self.repository.list_agents()
        return {
            "count": len(items),
            "states": {item["agent_id"]: item["state"] for item in items},
        }
