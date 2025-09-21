"""HTTP server that connects Ropebot events to the DJMAX controller."""
from __future__ import annotations

import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

from .csv_loader import Song, SongLibrary
from .djmax_control import ControllerResult, DjmaxController

LOGGER = logging.getLogger(__name__)


class CommandError(RuntimeError):
    """Raised when a command cannot be processed."""


class CommandProcessor:
    """Coordinates between the HTTP server, library and controller."""

    def __init__(self, library: SongLibrary, controller: DjmaxController) -> None:
        self.library = library
        self.controller = controller

    def status(self) -> dict:
        return {
            "status": "ok",
            "songs": len(tuple(self.library.songs)),
            "dryRun": self.controller.dry_run,
        }

    def _resolve_song(self, payload: dict) -> Song:
        title_number = _first_not_none(
            payload.get("titleNumber"),
            payload.get("title_number"),
            payload.get("titleId"),
            payload.get("title_id"),
            payload.get("tileId"),
            payload.get("tile_id"),
            payload.get("id"),
        )
        if title_number:
            song = self.library.find_by_title_number(str(title_number))
            if song is None:
                song = self.library.find_by_tile_id(str(title_number))
            if song is not None:
                return song
        title = payload.get("title")
        if title:
            song = self.library.find_by_title(str(title))
            if song is not None:
                return song
        raise CommandError("Unable to resolve song from payload.")

    def play_song(self, payload: dict) -> dict:
        song = self._resolve_song(payload)
        result: ControllerResult = self.controller.play_song(song)
        if not result.success:
            raise CommandError(result.message)
        return {
            "status": "ok",
            "song": song.to_dict(),
            "message": result.message,
        }

    def list_songs(self, group_key: Optional[str] = None) -> dict:
        if group_key:
            songs = [song.to_dict() for song in self.library.list_group(group_key)]
        else:
            songs = [song.to_dict() for song in self.library.songs]
        return {
            "status": "ok",
            "songs": songs,
        }


def _read_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    body = handler.rfile.read(length).decode("utf-8")
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:  # pragma: no cover - guard
        raise CommandError(f"Invalid JSON payload: {exc}")


def _first_not_none(*values):
    for value in values:
        if value not in (None, ""):
            return value
    return None


class CommandHandler(BaseHTTPRequestHandler):
    """Request handler that exposes the command API."""

    server: "CommandHTTPServer"

    def log_message(self, format: str, *args) -> None:  # noqa: A003 - BaseHTTPRequestHandler API
        LOGGER.info("%s - %s", self.client_address[0], format % args)

    # Helper functions -------------------------------------------------
    def _send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        LOGGER.error("%s", message)
        self._send_json(status, {"status": "error", "message": message})

    def do_OPTIONS(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler naming
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    # GET --------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler naming
        parsed = urlparse(self.path)
        if parsed.path == "/status":
            payload = self.server.processor.status()
            self._send_json(HTTPStatus.OK, payload)
            return
        if parsed.path == "/songs":
            params = parse_qs(parsed.query)
            group_key = None
            if "group" in params:
                group_values = params.get("group")
                if group_values:
                    group_key = group_values[0]
            payload = self.server.processor.list_songs(group_key)
            self._send_json(HTTPStatus.OK, payload)
            return
        self._send_error(HTTPStatus.NOT_FOUND, f"Unknown path: {parsed.path}")

    # POST -------------------------------------------------------------
    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler naming
        parsed = urlparse(self.path)
        if parsed.path == "/play":
            try:
                payload = _read_body(self)
                result = self.server.processor.play_song(payload)
            except CommandError as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            self._send_json(HTTPStatus.OK, result)
            return
        self._send_error(HTTPStatus.NOT_FOUND, f"Unknown path: {parsed.path}")


class CommandHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, processor: CommandProcessor):
        super().__init__(server_address, RequestHandlerClass)
        self.processor = processor


def create_server(host: str, port: int, processor: CommandProcessor) -> CommandHTTPServer:
    return CommandHTTPServer((host, port), CommandHandler, processor)
