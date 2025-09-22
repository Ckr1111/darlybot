"""System tray integration for the desktop helper application."""
from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from typing import Callable

import pystray
from pystray import Menu, MenuItem as Item
from PIL import Image

APP_NAME = "B300 Helper"
OPEN_URL = "https://b300.vercel.app"

__all__ = [
    "APP_NAME",
    "OPEN_URL",
    "create_tray_icon",
    "load_icon",
    "resource_path",
    "run_tray",
]


def resource_path(relative: str) -> Path:
    """Resolve the path to bundled resources.

    When packaged with PyInstaller the data files are copied to the temporary
    ``_MEIPASS`` directory.  During normal execution we refer to the package's
    directory directly.
    """

    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / relative


def load_icon() -> Image.Image:
    """Return the icon image used for the tray."""

    ico_path = resource_path("icon.ico")
    with Image.open(ico_path) as image:
        return image.copy()


def create_tray_icon(on_quit: Callable[[], None]) -> pystray.Icon:
    """Build the :class:`pystray.Icon` with menu handlers wired up."""

    image = load_icon()

    def handle_open(icon: pystray.Icon, item: Item) -> None:  # pragma: no cover - UI
        webbrowser.open(OPEN_URL)

    def handle_quit(icon: pystray.Icon, item: Item) -> None:  # pragma: no cover - UI
        try:
            on_quit()
        finally:
            icon.visible = False
            icon.stop()

    menu = Menu(
        Item("웹 열기", handle_open, default=True),
        Item("종료", handle_quit),
    )
    return pystray.Icon(APP_NAME, image, APP_NAME, menu)


def run_tray(on_quit: Callable[[], None]) -> None:
    """Create and run the system tray icon until the app is closed."""

    icon = create_tray_icon(on_quit)
    try:
        icon.run()
    except KeyboardInterrupt:  # pragma: no cover - graceful shutdown
        icon.visible = False
        icon.stop()
        raise
