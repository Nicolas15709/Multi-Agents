from __future__ import annotations

import asyncio
import contextlib
import json
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Set
from urllib.parse import parse_qs, urlparse

from websockets.exceptions import ConnectionClosed
from websockets.server import WebSocketServerProtocol, serve

try:
    from .auth import verify_jwt
except ImportError:  # pragma: no cover
    from auth import verify_jwt


@dataclass
class WebSocketPublisher:
    config: object
    last_payload: Optional[Dict] = None
    _clients: Set[WebSocketServerProtocol] = field(default_factory=set, init=False)
    _loop: Optional[asyncio.AbstractEventLoop] = field(default=None, init=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False)
    _started: bool = field(default=False, init=False)
    _server: Optional[object] = field(default=None, init=False)

    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        # ── Token authentication ──────────────────────────────────────────
        jwt_secret = getattr(self.config, "jwt_secret", "").strip()
        static_token = getattr(self.config, "api_auth_token", "").strip()

        if jwt_secret or static_token:
            # Extract ?token= from the WebSocket handshake URL
            ws_path = getattr(websocket, "path", "") or ""
            qs = parse_qs(urlparse(ws_path).query)
            submitted_token = (qs.get("token") or [""])[0]

            if jwt_secret:
                if verify_jwt(submitted_token, jwt_secret) is None:
                    await websocket.close(4001, "unauthorized")
                    return
            else:
                # Legacy static-token fallback
                import hmac as _hmac
                try:
                    ok = _hmac.compare_digest(
                        submitted_token.encode("utf-8"),
                        static_token.encode("utf-8"),
                    )
                except Exception:
                    ok = False
                if not ok:
                    await websocket.close(4001, "unauthorized")
                    return

        self._clients.add(websocket)
        try:
            if self.last_payload is not None:
                await websocket.send(json.dumps({"type": "snapshot", "payload": self.last_payload}))
            async for _message in websocket:
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
        self._server = await serve(self._handler, self.config.websocket_host, self.config.websocket_port)
        await self._server.wait_closed()

    def start(self) -> None:
        if not getattr(self.config, "websocket_enabled", False) or self._started:
            return

        def runner() -> None:
            loop = asyncio.new_event_loop()
            self._loop = loop
            asyncio.set_event_loop(loop)
            loop.create_task(self._server_main())
            loop.run_forever()

            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            with contextlib.suppress(Exception):
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()

        self._thread = threading.Thread(target=runner, name="virtual-agency-ws", daemon=True)
        self._thread.start()
        self._started = True

    def publish_snapshot(self, payload: Dict) -> None:
        self.last_payload = payload
        self.start()

        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast(payload), self._loop)

    async def _shutdown_async(self) -> None:
        for client in list(self._clients):
            with contextlib.suppress(Exception):
                await client.close()
        self._clients.clear()

        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    def stop(self) -> None:
        if not self._loop or not self._loop.is_running():
            return

        future = asyncio.run_coroutine_threadsafe(self._shutdown_async(), self._loop)
        with contextlib.suppress(Exception):
            future.result(timeout=3)
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._started = False

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

