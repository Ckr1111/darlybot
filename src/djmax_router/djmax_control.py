"""Control utilities for interacting with the DJMAX RESPECT V client."""
from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from typing import Dict

from .csv_loader import Song

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - Windows-specific dependency
    if sys.platform == "win32":
        import win32api  # type: ignore
        import win32con  # type: ignore
        import win32gui  # type: ignore
    else:  # pragma: no cover - non-Windows
        win32api = None  # type: ignore
        win32con = None  # type: ignore
        win32gui = None  # type: ignore
except Exception:  # pragma: no cover - import guard
    LOGGER.exception("Failed to import win32 modules; running in dry-run mode.")
    win32api = None  # type: ignore
    win32con = None  # type: ignore
    win32gui = None  # type: ignore


VK_CODE: Dict[str, int] = {
    letter: code for letter, code in zip(
        "abcdefghijklmnopqrstuvwxyz",
        range(0x41, 0x41 + 26),
    )
}
VK_CODE.update({
    "up": 0x26,
    "down": 0x28,
})


@dataclass
class ControllerResult:
    success: bool
    message: str


class DjmaxController:
    """Sends keystrokes to the DJMAX RESPECT V window."""

    def __init__(
        self,
        window_title: str = "DJMAX RESPECT V",
        key_interval: float = 0.05,
        letter_delay: float = 0.12,
        arrow_delay: float = 0.05,
        dry_run: bool | None = None,
    ) -> None:
        self.window_title = window_title
        self.key_interval = key_interval
        self.letter_delay = letter_delay
        self.arrow_delay = arrow_delay
        if dry_run is None:
            dry_run = sys.platform != "win32" or win32api is None
        self.dry_run = dry_run
        if self.dry_run:
            LOGGER.warning("DjmaxController running in dry-run mode; no keys will be sent.")

    def focus_window(self) -> bool:
        if self.dry_run:
            return True
        assert win32gui is not None and win32con is not None
        hwnd = win32gui.FindWindow(None, self.window_title)
        if hwnd == 0:
            LOGGER.error("Could not locate window titled '%s'", self.window_title)
            return False
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.05)
        return True

    def _send_virtual_key(self, key: str, repeat: int = 1, delay: float = 0.05) -> None:
        key = key.lower()
        if key not in VK_CODE:
            raise ValueError(f"Unsupported key: {key}")
        if self.dry_run:
            LOGGER.info("Simulating key press: %s x%d", key, repeat)
            time.sleep(delay * repeat)
            return
        assert win32api is not None
        vk_code = VK_CODE[key]
        scan_code = win32api.MapVirtualKey(vk_code, 0)
        for _ in range(repeat):
            win32api.keybd_event(vk_code, scan_code, 0, 0)
            time.sleep(self.key_interval)
            win32api.keybd_event(vk_code, scan_code, 2, 0)
            time.sleep(delay)

    def send_letter(self, letter: str) -> None:
        self._send_virtual_key(letter, repeat=1, delay=self.letter_delay)

    def send_arrow(self, direction: str, count: int) -> None:
        if count <= 0:
            return
        self._send_virtual_key(direction, repeat=count, delay=self.arrow_delay)

    def play_song(self, song: Song) -> ControllerResult:
        if not self.focus_window():
            return ControllerResult(False, "Game window not found.")
        try:
            self.send_letter(song.group_key)
            if song.index_in_group:
                self.send_arrow("down", song.index_in_group)
        except ValueError as exc:  # Unsupported key
            LOGGER.error("Failed to send keys: %s", exc)
            return ControllerResult(False, str(exc))
        return ControllerResult(True, "Keys sent successfully.")
