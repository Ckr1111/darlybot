"""Input controller implementations."""
from __future__ import annotations

import logging
import time
from typing import Iterable, List, Sequence

from .navigator import InputController

__all__ = [
    "DJMaxInputController",
    "SimulatedInputController",
]

_LOGGER = logging.getLogger(__name__)


class DJMaxInputController(InputController):
    """Send key presses directly to the DJMAX RESPECT V client."""

    def __init__(
        self,
        *,
        window_title: str = "DJMAX RESPECT V",
        activation_delay: float = 0.3,
        key_delay: float = 0.05,
    ) -> None:
        self.window_title = window_title
        self.activation_delay = activation_delay
        self.key_delay = key_delay

    def focus_window(self) -> None:
        try:
            import pygetwindow  # type: ignore
        except ImportError as exc:  # pragma: no cover - requires Windows
            raise RuntimeError(
                "pygetwindow 모듈이 설치되어 있지 않습니다. 'pip install pygetwindow' 를 실행해주세요."
            ) from exc

        windows = pygetwindow.getWindowsWithTitle(self.window_title)
        if not windows:
            raise RuntimeError(
                f"'{self.window_title}' 제목의 창을 찾을 수 없습니다. DJMAX RESPECT V 가 실행 중인지 확인해주세요."
            )

        window = windows[0]
        if window.isMinimized:
            window.restore()
            time.sleep(self.activation_delay)
        window.activate()
        time.sleep(self.activation_delay)
        _LOGGER.debug("Focused DJMAX window '%s'", self.window_title)

    def send_keys(self, keys: Iterable[str]) -> None:
        try:
            import pyautogui  # type: ignore
        except ImportError as exc:  # pragma: no cover - requires Windows
            raise RuntimeError(
                "pyautogui 모듈이 설치되어 있지 않습니다. 'pip install pyautogui' 를 실행해주세요."
            ) from exc

        for key in keys:
            _LOGGER.debug("Pressing key: %s", key)
            pyautogui.press(key)
            time.sleep(self.key_delay)


class SimulatedInputController(InputController):
    """A testing helper that only records the keys that would be sent."""

    def __init__(self) -> None:
        self.focused: bool = False
        self.sent_keys: List[str] = []

    def focus_window(self) -> None:  # pragma: no cover - trivial setter
        self.focused = True

    def send_keys(self, keys: Iterable[str]) -> None:
        self.sent_keys.extend(keys)

    def reset(self) -> None:
        self.focused = False
        self.sent_keys.clear()

    def last_sequence(self) -> Sequence[str]:
        return tuple(self.sent_keys)
