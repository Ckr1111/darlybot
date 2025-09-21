"""HTTP bridge used by the desktop helper application."""
from __future__ import annotations

import json
import logging
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .navigator import NavigationError, SongNavigator
from .song_index import SongIndex, SongNotFoundError

__all__ = ["SongServer"]

_LOGGER = logging.getLogger(__name__)


class SongServer:
    """Expose the :class:`SongNavigator` as an HTTP API."""

    def __init__(
        self,
        navigator: SongNavigator,
        *,
        index: SongIndex,
        host: str = "127.0.0.1",
        port: int = 8972,
        allow_cors: bool = True,
    ) -> None:
        self.navigator = navigator
        self.index = index
        self.host = host
        self.port = port
        self.allow_cors = allow_cors
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    # Lifecycle ---------------------------------------------------------
    def start(self) -> None:
        if self._httpd is not None:  # pragma: no cover - defensive
            raise RuntimeError("서버가 이미 실행 중입니다.")

        handler = self._build_handler()
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        # If ``port`` is 0 the OS will pick an available port.  Surface the
        # actual port so integrations (and tests) can discover it.
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, name="SongServer", daemon=True
        )
        self._thread.start()
        _LOGGER.info("Song server listening on http://%s:%s", self.host, self.port)

    def serve_forever(self) -> None:  # pragma: no cover - integration utility
        self.start()
        try:
            while self._thread and self._thread.is_alive():
                self._thread.join(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        if self._httpd is None:
            return
        _LOGGER.info("Stopping song server")
        self._httpd.shutdown()
        self._httpd.server_close()
        self._httpd = None
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None

    # Handler -----------------------------------------------------------
    def _build_handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "DarlyBot/1.0"

            def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover
                _LOGGER.info("%s - %s", self.address_string(), format % args)

            # Utilities -------------------------------------------------
            def _set_headers(self, status: HTTPStatus, *, content_type: str = "application/json") -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                if server.allow_cors:
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Access-Control-Allow-Headers", "content-type")
                    self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
                self.end_headers()

            def _write_json(self, data: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
                payload = json.dumps(data).encode("utf-8")
                self._set_headers(status)
                self.wfile.write(payload)

            def _write_json_error(self, status: HTTPStatus, message: str) -> None:
                self._write_json({"error": message}, status)

            def _parse_path(self) -> str:
                return urlparse(self.path).path

            def _read_json(self) -> Dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0"))
                if not length:
                    return {}
                body = self.rfile.read(length)
                try:
                    return json.loads(body.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    raise ValueError("잘못된 JSON 데이터입니다.") from exc

            # HTTP verbs ------------------------------------------------
            def do_OPTIONS(self) -> None:  # pragma: no cover - browser handshake
                self._set_headers(HTTPStatus.NO_CONTENT)

            def do_GET(self) -> None:
                path = self._parse_path()
                if path == "/ping":
                    self._write_json({"status": "ok"})
                elif path == "/songs":
                    songs = [entry.to_payload() for entry in server.index]
                    self._write_json({"songs": songs})
                else:
                    self._write_json_error(HTTPStatus.NOT_FOUND, "알 수 없는 경로입니다.")

            def do_POST(self) -> None:
                path = self._parse_path()
                if path == "/navigate":
                    self._handle_navigate()
                else:
                    self._write_json_error(HTTPStatus.NOT_FOUND, "알 수 없는 경로입니다.")

            # Endpoint handlers ----------------------------------------
            def _handle_navigate(self) -> None:
                try:
                    payload = self._read_json()
                except ValueError as exc:
                    self._write_json_error(HTTPStatus.BAD_REQUEST, str(exc))
                    return

                title_number = payload.get("title_number")
                title = payload.get("title")
                dry_run = bool(payload.get("dry_run", False))

                try:
                    result = server.navigator.navigate(
                        title_number=title_number, title=title, dry_run=dry_run
                    )
                except SongNotFoundError as exc:
                    self._write_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                    return
                except NavigationError as exc:
                    self._write_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return

                response = {
                    "title": result.entry.title,
                    "title_number": result.entry.title_number,
                    "letter": result.entry.letter,
                    "keys": list(result.keys),
                    "performed": result.performed,
                }
                self._write_json(response)

        return Handler
