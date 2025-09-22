"""System tray integration for the helper application."""

from __future__ import annotations

import logging
import threading
import webbrowser
from importlib import resources
from typing import Optional

import pystray
from PIL import Image

__all__ = ["SystemTrayController"]

_LOGGER = logging.getLogger(__name__)
_ICON_RESOURCE = "icon.ico"
_ICON_NAME = "darlybot"
_ICON_TOOLTIP = "Darlybot Helper"
_DEFAULT_WEB_URL = "https://b300.vercel.app"


class SystemTrayController:
    """Manage the application system tray icon."""

    def __init__(self, stop_event: threading.Event, *, web_url: str = _DEFAULT_WEB_URL) -> None:
        self._stop_event = stop_event
        self.web_url = web_url
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None
        self._image: Optional[Image.Image] = None

    # Lifecycle ---------------------------------------------------------
    def start(self) -> None:
        """Create the system tray icon and begin processing events."""

        if self._thread and self._thread.is_alive():  # pragma: no cover - defensive
            raise RuntimeError("Tray icon is already running")

        self._image = self._load_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("웹 열기", self._handle_open_web),
            pystray.MenuItem("닫기", self._handle_exit_application),
        )
        self._icon = pystray.Icon(
            _ICON_NAME,
            icon=self._image,
            title=_ICON_TOOLTIP,
            menu=menu,
        )
        self._thread = threading.Thread(
            target=self._run_icon,
            name="SystemTray",
            daemon=True,
        )
        self._thread.start()
        _LOGGER.debug("System tray icon started")

    def stop(self) -> None:
        """Stop the tray icon event loop and clean up resources."""

        self._stop_event.set()
        icon = self._icon
        if icon is not None:
            try:
                icon.stop()
            except Exception as exc:  # pragma: no cover - best effort cleanup
                _LOGGER.debug("Failed to stop tray icon cleanly: %s", exc)
        thread = self._thread
        if thread is not None:
            thread.join(timeout=1)
        self._icon = None
        self._thread = None

    # Internal helpers --------------------------------------------------
    def _run_icon(self) -> None:
        icon = self._icon
        if icon is None:  # pragma: no cover - defensive
            return

        def setup(tray_icon: pystray.Icon) -> None:
            tray_icon.visible = True

        try:
            icon.run(setup=setup)
        finally:
            self._stop_event.set()
            _LOGGER.debug("System tray icon stopped")

    def _load_icon_image(self) -> Image.Image:
        resource = resources.files(__package__) / _ICON_RESOURCE
        with resources.as_file(resource) as icon_path:
            with Image.open(icon_path) as image:
                return image.copy().convert("RGBA")

    def _handle_open_web(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        opened = webbrowser.open(self.web_url)
        if not opened:
            _LOGGER.warning("웹 브라우저를 열 수 없습니다: %s", self.web_url)

    def _handle_exit_application(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._stop_event.set()
        icon.visible = False
        icon.stop()

