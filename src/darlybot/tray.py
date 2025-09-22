"""System tray integration for the desktop helper."""
from __future__ import annotations

import logging
import webbrowser
from pathlib import Path
from typing import Any, Optional

try:  # pragma: no cover - optional dependency at runtime
    import pystray
    from PIL import Image
except Exception:  # pragma: no cover - gracefully handle missing libraries
    pystray = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]

__all__ = ["SystemTray", "TrayUnavailableError"]


_LOGGER = logging.getLogger(__name__)


class TrayUnavailableError(RuntimeError):
    """Raised when a system tray icon cannot be created."""


class SystemTray:
    """Encapsulate the behaviour of the helper's system tray icon."""

    def __init__(
        self,
        *,
        icon_path: Optional[Path],
        tooltip: str,
        open_url: str,
    ) -> None:
        if pystray is None or Image is None:
            raise TrayUnavailableError("pystray 또는 Pillow 라이브러리를 찾을 수 없습니다.")

        self._open_url = open_url
        self._running = False

        image = self._load_image(icon_path)

        menu = pystray.Menu(
            pystray.MenuItem("웹 열기", self._handle_open_url),
            pystray.MenuItem("닫기", self._handle_quit),
        )

        self._icon = pystray.Icon(
            "darlybot",  # identifier
            image,
            tooltip,
            menu=menu,
        )

    # Lifecycle -----------------------------------------------------
    def run(self) -> None:
        """Block until the tray icon is closed."""

        if pystray is None:
            raise TrayUnavailableError("pystray is not available")

        def _setup(icon: pystray.Icon) -> None:
            self._running = True
            icon.visible = True

        try:
            self._icon.run(_setup)
        finally:
            self._running = False

    def stop(self) -> None:
        """Remove the icon from the system tray if it is running."""

        if pystray is None:
            return

        try:
            self._icon.visible = False
        except Exception:  # pragma: no cover - backend specific safety
            pass

        if self._running:
            try:
                self._icon.stop()
            except Exception:  # pragma: no cover - backend specific safety
                _LOGGER.debug("Failed to stop tray icon", exc_info=True)

        self._running = False

    # Event handlers -----------------------------------------------
    def _handle_quit(self, icon: pystray.Icon, item: Any) -> None:
        del item  # unused
        icon.visible = False
        icon.stop()

    def _handle_open_url(self, icon: pystray.Icon, item: Any) -> None:
        del icon, item  # unused
        try:
            webbrowser.open(self._open_url, new=2)
        except Exception as exc:  # pragma: no cover - platform specific
            _LOGGER.warning("웹 페이지를 여는 데 실패했습니다: %s", exc)

    # Utilities -----------------------------------------------------
    def _load_image(self, icon_path: Optional[Path]):
        assert Image is not None  # for type checkers

        if icon_path and icon_path.exists():
            try:
                with Image.open(icon_path) as source:
                    return source.copy()
            except Exception as exc:
                _LOGGER.debug("Failed to load tray icon from %s: %s", icon_path, exc)

        _LOGGER.debug("Falling back to generated tray icon")
        return Image.new("RGBA", (64, 64), (34, 197, 94, 255))

