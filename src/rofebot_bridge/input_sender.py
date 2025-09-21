"""Send key sequences to the DJMAX RESPECT V window."""

from __future__ import annotations

import logging
import platform
import time
from dataclasses import dataclass
from typing import Iterable, Optional

from .models import SearchPlan

_LOGGER = logging.getLogger(__name__)


class InputSendError(RuntimeError):
    """Raised when the program could not control the DJMAX window."""


@dataclass
class DJMaxInputSender:
    window_title: str = "DJMAX RESPECT V"
    key_delay: float = 0.05
    focus_delay: float = 0.15
    dry_run: bool = False

    def execute_plan(self, plan: SearchPlan) -> None:
        sequence = plan.as_key_sequence()
        if not sequence:
            _LOGGER.info("Nothing to send for %s", plan.song.display_label())
            return

        _LOGGER.info(
            "Executing plan for %s: base=%s offset=%s", plan.song.display_label(), plan.base_key, plan.offset
        )

        if not self.dry_run:
            self._focus_window()
        else:
            _LOGGER.debug("Dry-run mode: skipping window focus")

        self._send_sequence(sequence)

    # -- internals ---------------------------------------------------------
    def _focus_window(self) -> None:
        if platform.system() != "Windows":
            raise InputSendError("Key sending is only supported on Windows")

        try:
            import win32con
            import win32gui
        except ImportError as exc:  # pragma: no cover - only executed on Windows
            raise InputSendError("pywin32 is required to focus the DJMAX window") from exc

        title_lower = self.window_title.casefold()
        target_hwnd: Optional[int] = None

        def _enum_handler(hwnd: int, _ctx: Optional[object]) -> bool:
            nonlocal target_hwnd
            window_title = win32gui.GetWindowText(hwnd)
            if window_title and title_lower in window_title.casefold():
                target_hwnd = hwnd
                return False
            return True

        win32gui.EnumWindows(_enum_handler, None)

        if not target_hwnd:
            raise InputSendError(f"Could not find window titled '{self.window_title}'")

        win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        try:
            win32gui.SetForegroundWindow(target_hwnd)
        except Exception:  # pragma: no cover - Windows specific fallback path
            self._force_foreground(target_hwnd)

        time.sleep(self.focus_delay)

    def _force_foreground(self, hwnd: int) -> None:  # pragma: no cover - requires Windows
        import ctypes

        user32 = ctypes.windll.user32
        foreground = user32.GetForegroundWindow()
        current_thread = user32.GetCurrentThreadId()
        process_id = ctypes.c_ulong()
        foreground_thread = user32.GetWindowThreadProcessId(foreground, ctypes.byref(process_id))
        if foreground_thread and foreground_thread != current_thread:
            user32.AttachThreadInput(foreground_thread, current_thread, True)
            user32.BringWindowToTop(hwnd)
            user32.ShowWindow(hwnd, 5)
            user32.SetForegroundWindow(hwnd)
            user32.AttachThreadInput(foreground_thread, current_thread, False)
        else:
            user32.SetForegroundWindow(hwnd)

    def _send_sequence(self, sequence: Iterable[str]) -> None:
        if self.dry_run:
            _LOGGER.info("Dry run: would send %s", " ".join(sequence))
            return

        if platform.system() != "Windows":
            raise InputSendError("Key sending is only supported on Windows")

        try:
            from pywinauto import keyboard
        except ImportError as exc:  # pragma: no cover - Windows specific
            raise InputSendError("pywinauto is required to send key presses") from exc

        for token in sequence:
            _LOGGER.debug("Sending key %s", token)
            keyboard.send_keys(token, with_spaces=True, pause=self.key_delay)


__all__ = ["DJMaxInputSender", "InputSendError"]
