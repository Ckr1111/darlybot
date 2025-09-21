"""Control DJMAX RESPECT V via synthetic keyboard events on Windows."""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass

try:  # pragma: no cover - platform specific
    import win32api  # type: ignore
    import win32con  # type: ignore
    import win32gui  # type: ignore
except ImportError:  # pragma: no cover - platform specific
    win32api = None  # type: ignore
    win32con = None  # type: ignore
    win32gui = None  # type: ignore

from .navigator import NavigationPlan

logger = logging.getLogger(__name__)


class WindowNotFoundError(RuntimeError):
    """Raised when the DJMAX RESPECT V window could not be located."""


@dataclass
class ControllerConfig:
    window_title: str = "DJMAX RESPECT V"
    key_delay: float = 0.05
    jump_delay: float = 0.2
    dry_run: bool = False


class DJMaxController:
    """Send keyboard input to DJMAX RESPECT V based on navigation plans."""

    def __init__(self, window_title: str = "DJMAX RESPECT V", *, key_delay: float = 0.05, jump_delay: float = 0.2, dry_run: bool | None = None) -> None:
        self.window_title = window_title
        self.key_delay = key_delay
        self.jump_delay = jump_delay
        if dry_run is None:
            dry_run = sys.platform != "win32" or win32api is None
        self.dry_run = dry_run
        if not self.dry_run and (win32api is None or win32con is None or win32gui is None):
            raise RuntimeError("pywin32 is required to control DJMAX RESPECT V on Windows.")

    def navigate(self, plan: NavigationPlan) -> None:
        """Execute the navigation plan inside DJMAX RESPECT V."""

        logger.info("Navigating to '%s' via %s", plan.title, plan.keystrokes())
        if self.dry_run:
            # Dry-run mode only logs the navigation request.
            return

        self._focus_window()
        if plan.letter:
            self._press_key(plan.letter)
            time.sleep(self.jump_delay)
        direction = "down" if plan.offset >= 0 else "up"
        for _ in range(abs(plan.offset)):
            self._press_key(direction)
            time.sleep(self.key_delay)

    def _focus_window(self) -> None:
        if self.dry_run:
            return
        assert win32gui is not None and win32con is not None
        hwnd = win32gui.FindWindow(None, self.window_title)
        if not hwnd:
            raise WindowNotFoundError(f"Window titled '{self.window_title}' was not found.")
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.05)

    def _press_key(self, key: str) -> None:
        if self.dry_run:
            logger.debug("Dry-run key press: %s", key)
            return
        assert win32api is not None and win32con is not None
        vk = self._vk_code(key)
        scan = win32api.MapVirtualKey(vk, 0)
        win32api.keybd_event(vk, scan, 0, 0)
        time.sleep(0.01)
        win32api.keybd_event(vk, scan, win32con.KEYEVENTF_KEYUP, 0)

    @staticmethod
    def _vk_code(key: str) -> int:
        key_lower = key.lower()
        if key_lower == "down":
            assert win32con is not None
            return win32con.VK_DOWN
        if key_lower == "up":
            assert win32con is not None
            return win32con.VK_UP
        if len(key_lower) == 1 and "a" <= key_lower <= "z":
            return ord(key_lower.upper())
        raise ValueError(f"Unsupported key: {key}")


__all__ = ["DJMaxController", "ControllerConfig", "WindowNotFoundError"]
