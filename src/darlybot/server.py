"""A small HTTP/WebSocket server bridging Lopebot to DJMAX RESPECT V."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

from aiohttp import WSMsgType, web

from .controller import DJMaxController
from .navigator import SongNavigator

logger = logging.getLogger(__name__)


class BridgeServer:
    """Encapsulates the Lopebot bridge server state."""

    def __init__(self, navigator: SongNavigator, controller: DJMaxController, *, allow_origin: str | None = "*") -> None:
        self.navigator = navigator
        self.controller = controller
        self.allow_origin = allow_origin
        self._clients: set[web.WebSocketResponse] = set()

    def add_routes(self, app: web.Application) -> None:
        app.router.add_get("/status", self.handle_status)
        app.router.add_get("/songs", self.handle_songs)
        app.router.add_get("/ws", self.handle_websocket)
        app.on_shutdown.append(self.on_shutdown)

    async def on_shutdown(self, app: web.Application) -> None:  # pragma: no cover - exercised by aiohttp
        for ws in set(self._clients):
            await ws.close(code=1001, message="Server shutdown")

    def _json_response(self, data: Dict[str, Any]) -> web.Response:
        response = web.json_response(data)
        if self.allow_origin:
            response.headers["Access-Control-Allow-Origin"] = self.allow_origin
        return response

    async def handle_status(self, request: web.Request) -> web.Response:
        data = {
            "status": "ok",
            "songs": self.navigator.song_count,
            "letters": self.navigator.available_letters,
            "dryRun": self.controller.dry_run,
        }
        return self._json_response(data)

    async def handle_songs(self, request: web.Request) -> web.Response:
        return self._json_response({"songs": self.navigator.song_titles})

    async def handle_websocket(self, request: web.Request) -> web.StreamResponse:
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)

        self._clients.add(ws)
        await ws.send_json(
            {
                "type": "ready",
                "songs": self.navigator.song_count,
                "letters": self.navigator.available_letters,
                "dryRun": self.controller.dry_run,
            }
        )

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_ws_message(ws, msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error("WebSocket error: %s", ws.exception())
                    break
        finally:
            self._clients.discard(ws)
        return ws

    async def _handle_ws_message(self, ws: web.WebSocketResponse, data: str) -> None:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            await ws.send_json({"type": "error", "message": "Invalid JSON payload"})
            return

        message_type = payload.get("type")
        if message_type == "ping":
            await ws.send_json({"type": "pong"})
            return
        if message_type == "navigate":
            await self._handle_navigate(ws, payload)
            return
        await ws.send_json({"type": "error", "message": f"Unsupported message type: {message_type}"})

    async def _handle_navigate(self, ws: web.WebSocketResponse, payload: Dict[str, Any]) -> None:
        title = payload.get("title")
        if not title:
            await ws.send_json({"type": "navigate", "status": "error", "message": "Missing 'title'"})
            return
        logger.info("Navigation requested for '%s'", title)
        try:
            plan = self.navigator.plan_for_title(title)
        except KeyError as exc:
            await ws.send_json({"type": "navigate", "status": "error", "message": str(exc)})
            return

        await ws.send_json({"type": "navigate", "status": "planning", "plan": plan.to_dict()})
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.controller.navigate, plan)
        except Exception as exc:  # pragma: no cover - requires Windows runtime
            logger.exception("Navigation failed: %s", exc)
            await ws.send_json({"type": "navigate", "status": "error", "message": str(exc)})
        else:
            await ws.send_json({"type": "navigate", "status": "done", "plan": plan.to_dict()})


def create_app(navigator: SongNavigator, controller: DJMaxController, *, allow_origin: str | None = "*") -> web.Application:
    """Create an aiohttp application exposing the Lopebot bridge endpoints."""

    app = web.Application()
    server = BridgeServer(navigator, controller, allow_origin=allow_origin)
    server.add_routes(app)
    app["bridge_server"] = server
    return app


__all__ = ["create_app", "BridgeServer"]
