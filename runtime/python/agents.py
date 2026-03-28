import json
from pathlib import Path
from typing import Dict, List

from models import AgentRecord


class AgentRegistry:
    def __init__(self, path: str):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def list_agents(self) -> List[Dict]:
        return self.data.get("agents", [])

    def to_records(self) -> List[AgentRecord]:
        return [
            AgentRecord(
                agent_id=item["id"],
                display_name=item["display_name"],
                role=item["role"],
                personality=item.get("personality"),
            )
            for item in self.list_agents()
        ]
