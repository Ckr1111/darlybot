"""HTTP bridge exposed to the RofeBot webpage."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

from .catalog import AmbiguousSongError, SongNotFoundError
from .input_sender import DJMaxInputSender, InputSendError
from .planner import PlanResult, SearchPlanner

_LOGGER = logging.getLogger(__name__)


@dataclass
class BridgeContext:
    planner: SearchPlanner
    sender: DJMaxInputSender


class _RequestHandler(BaseHTTPRequestHandler):
    server_version = "RofeBotBridge/1.0"

    def do_OPTIONS(self) -> None:  # noqa: N802 - required method name
        self._send_cors_headers()
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "/status":
            context: BridgeContext = self.server.context  # type: ignore[attr-defined]
            payload = {
                "status": "ok",
                "songCount": len(context.planner.catalog.songs),
                "availableKeys": sorted(context.planner.catalog.first_by_key.keys()),
            }
            self._write_json(payload)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/select":
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
            return

        try:
            payload = self._read_json()
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        context: BridgeContext = self.server.context  # type: ignore[attr-defined]

        try:
            result = context.planner.plan_from_payload(payload)
        except AmbiguousSongError as exc:
            self._write_json({"error": "Ambiguous song", "detail": str(exc)}, status=HTTPStatus.CONFLICT)
            return
        except SongNotFoundError as exc:
            self._write_json({"error": "Song not found", "detail": str(exc)}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            context.sender.execute_plan(result.plan)
        except InputSendError as exc:
            self._write_json({"error": "Input error", "detail": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._write_json(_result_to_payload(result))

    # -- helpers -----------------------------------------------------------
    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length) if length else b""
        if not data:
            return {}
        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON payload") from exc

    def _write_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: D401 - inherited API
        _LOGGER.info("%s - %s", self.address_string(), format % args)


@dataclass
class BridgeServer:
    planner: SearchPlanner
    sender: DJMaxInputSender
    host: str = "127.0.0.1"
    port: int = 29184

    def serve_forever(self) -> None:
        handler_class = self._build_handler()
        httpd = ThreadingHTTPServer((self.host, self.port), handler_class)
        httpd.context = BridgeContext(self.planner, self.sender)  # type: ignore[attr-defined]

        _LOGGER.info("Listening on http://%s:%s", self.host, self.port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            _LOGGER.info("Shutting down bridge server")
        finally:
            httpd.server_close()

    def _build_handler(self) -> type[_RequestHandler]:
        return _RequestHandler


def _result_to_payload(result: PlanResult) -> Dict[str, Any]:
    return {
        "status": "ok",
        "song": {
            "title": result.match.song.title,
            "titleNumber": result.match.song.title_number,
            "jumpKey": result.plan.base_key,
            "offset": result.plan.offset,
        },
        "plan": {
            "direction": result.plan.direction,
            "arrowCount": result.plan.arrow_count,
            "sequence": result.plan.as_key_sequence(),
        },
    }


__all__ = ["BridgeServer", "BridgeContext"]
