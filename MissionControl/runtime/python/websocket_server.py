from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class WebSocketPublisher:
    config: object
    last_payload: Optional[Dict] = None

    def publish_snapshot(self, payload: Dict) -> None:
        self.last_payload = payload

    def summary(self) -> dict:
        return {
            "transport": "local_websocket",
            "status": "buffered-scaffold",
            "has_payload": self.last_payload is not None,
        }
