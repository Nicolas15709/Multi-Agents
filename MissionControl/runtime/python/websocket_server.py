from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from websockets.exceptions import ConnectionClosed
from websockets.server import WebSocketServerProtocol, serve


@dataclass
class WebSocketPublisher:
    config: object
    last_payload: Optional[Dict] = None
    _clients: Set[WebSocketServerProtocol] = field(default_factory=set, init=False)
    _loop: Optional[asyncio.AbstractEventLoop] = field(default=None, init=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False)
    _started: bool = field(default=False, init=False)

    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        self._clients.add(websocket)
        try:
            if self.last_payload is not None:
                await websocket.send(json.dumps({"type": "snapshot", "payload": self.last_payload}))
            async for _message in websocket:
                # Read-and-ignore for now; reserved for future commands/pings.
                pass
        except ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)

    async def _broadcast(self, payload: Dict) -> None:
        if not self._clients:
            return

        message = json.dumps({"type": "snapshot", "payload": payload})
        stale: Set[WebSocketServerProtocol] = set()
        for client in list(self._clients):
            try:
                await client.send(message)
            except ConnectionClosed:
                stale.add(client)
        for client in stale:
            self._clients.discard(client)

    async def _server_main(self) -> None:
        async with serve(self._handler, self.config.websocket_host, self.config.websocket_port):
            await asyncio.Future()

    def start(self) -> None:
        if not getattr(self.config, "websocket_enabled", False) or self._started:
            return

        def runner() -> None:
            loop = asyncio.new_event_loop()
            self._loop = loop
            asyncio.set_event_loop(loop)
            loop.create_task(self._server_main())
            loop.run_forever()

        self._thread = threading.Thread(target=runner, name="mission-control-ws", daemon=True)
        self._thread.start()
        self._started = True

    def publish_snapshot(self, payload: Dict) -> None:
        self.last_payload = payload
        self.start()

        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast(payload), self._loop)

    def summary(self) -> dict:
        return {
            "transport": "local_websocket",
            "status": "running" if self._started else "idle",
            "enabled": getattr(self.config, "websocket_enabled", False),
            "host": getattr(self.config, "websocket_host", "127.0.0.1"),
            "port": getattr(self.config, "websocket_port", 8765),
            "clients": len(self._clients),
            "has_payload": self.last_payload is not None,
        }
