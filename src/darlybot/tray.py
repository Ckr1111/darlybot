"""System tray integration for the desktop helper."""
from __future__ import annotations

import logging
import threading
import webbrowser
from importlib import resources
from typing import Callable

import pystray
from PIL import Image

_LOGGER = logging.getLogger(__name__)


def _load_icon_image() -> Image.Image:
    """Return the image used for the tray icon."""

    try:
        with resources.files("darlybot").joinpath("favicon.ico").open("rb") as handle:
            with Image.open(handle) as image:
                return image.convert("RGBA")
    except FileNotFoundError:
        _LOGGER.warning("Tray icon resource could not be found; using a blank icon.")
    except Exception:  # pragma: no cover - best-effort fallback
        _LOGGER.exception("Failed to load tray icon image; using a blank icon.")

    return Image.new("RGBA", (64, 64))


class SystemTray:
    """Expose basic controls via the operating system tray."""

    def __init__(self, *, on_quit: Callable[[], None], website_url: str) -> None:
        self._on_quit = on_quit
        self._website_url = website_url
        self._icon = pystray.Icon(
            "darlybot",
            icon=_load_icon_image(),
            title="Darlybot Helper",
            menu=pystray.Menu(
                pystray.MenuItem("웹 열기", self._handle_open_website),
                pystray.MenuItem("닫기", self._handle_quit),
            ),
        )
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        """Display the tray icon in a detached thread."""

        with self._lock:
            if self._running:
                return
            self._running = True

        # ``run_detached`` spawns the GUI loop on a dedicated thread so the
        # caller can continue running background work.
        self._icon.run_detached()

    def stop(self) -> None:
        """Hide and dispose of the tray icon if it is running."""

        with self._lock:
            if not self._running:
                return
            self._running = False

        try:
            self._icon.visible = False
        except Exception:  # pragma: no cover - backend specific behaviour
            pass
        self._icon.stop()

    # Menu callbacks -----------------------------------------------------
    def _handle_open_website(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        try:
            webbrowser.open(self._website_url, new=2, autoraise=True)
        except Exception:  # pragma: no cover - browser availability varies
            _LOGGER.exception("Failed to open the website from the tray menu.")

    def _handle_quit(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        try:
            self._on_quit()
        finally:
            self.stop()

