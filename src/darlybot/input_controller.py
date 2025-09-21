"""Input controller implementations."""
from __future__ import annotations

import logging
import time
from typing import Any, Iterable, List, Sequence

from .navigator import InputController
from .song_index import SCROLL_DOWN_KEY, SCROLL_UP_KEY

__all__ = [
    "DJMaxInputController",
    "SimulatedInputController",
]

_LOGGER = logging.getLogger(__name__)

_SPECIAL_KEY_NAMES = {
    "pageup": "page_up",
    "pagedown": "page_down",
    "pgup": "page_up",
    "pgdn": "page_down",
    "enter": "enter",
    "return": "enter",
    "escape": "esc",
    "esc": "esc",
    "space": "space",
    "tab": "tab",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "home": "home",
    "end": "end",
}


class DJMaxInputController(InputController):
    """Send key presses directly to the DJMAX RESPECT V client."""

    def __init__(
        self,
        *,
        window_title: str = "DJMAX RESPECT V",
        activation_delay: float = 0.3,
        key_delay: float = 0.02,
    ) -> None:
        self.window_title = window_title
        self.activation_delay = activation_delay
        self.key_delay = key_delay
        self._keyboard_module: Any | None = None
        self._keyboard_controller: Any | None = None
        self._mouse_module: Any | None = None
        self._mouse_controller: Any | None = None

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
        keyboard = None
        mouse = None

        for key in keys:
            if key == SCROLL_UP_KEY:
                _LOGGER.debug("Scrolling up via mouse wheel")
                if mouse is None:
                    mouse = self._ensure_mouse_controller()
                mouse.scroll(0, 1)
            elif key == SCROLL_DOWN_KEY:
                _LOGGER.debug("Scrolling down via mouse wheel")
                if mouse is None:
                    mouse = self._ensure_mouse_controller()
                mouse.scroll(0, -1)
            else:
                if keyboard is None:
                    keyboard = self._ensure_keyboard_controller()
                key_code = self._translate_key(key)
                _LOGGER.debug("Pressing key: %s", key)
                keyboard.tap(key_code)
            time.sleep(self.key_delay)

    # Internal utilities -------------------------------------------------
    def _ensure_keyboard_module(self):
        if self._keyboard_module is None:
            try:
                from pynput import keyboard as pynput_keyboard  # type: ignore
            except ImportError as exc:  # pragma: no cover - requires Windows
                raise RuntimeError(
                    "pynput 모듈이 설치되어 있지 않습니다. 'pip install pynput' 를 실행해주세요."
                ) from exc

            self._keyboard_module = pynput_keyboard
        return self._keyboard_module

    def _ensure_keyboard_controller(self):
        if self._keyboard_controller is None:
            keyboard_module = self._ensure_keyboard_module()
            self._keyboard_controller = keyboard_module.Controller()
        return self._keyboard_controller

    def _ensure_mouse_module(self):
        if self._mouse_module is None:
            try:
                from pynput import mouse as pynput_mouse  # type: ignore
            except ImportError as exc:  # pragma: no cover - requires Windows
                raise RuntimeError(
                    "pynput 모듈이 설치되어 있지 않습니다. 'pip install pynput' 를 실행해주세요."
                ) from exc

            self._mouse_module = pynput_mouse
        return self._mouse_module

    def _ensure_mouse_controller(self):
        if self._mouse_controller is None:
            mouse_module = self._ensure_mouse_module()
            self._mouse_controller = mouse_module.Controller()
        return self._mouse_controller

    def _translate_key(self, key: str):
        keyboard_module = self._ensure_keyboard_module()
        name = key.lower()
        attr_name = _SPECIAL_KEY_NAMES.get(name, name)
        attr_name = attr_name.replace(" ", "_")

        if hasattr(keyboard_module.Key, attr_name):
            return getattr(keyboard_module.Key, attr_name)

        if len(key) == 1:
            return keyboard_module.KeyCode.from_char(key)

        # F-keys (e.g. f1, f2)
        if name.startswith("f") and name[1:].isdigit():
            if hasattr(keyboard_module.Key, name):
                return getattr(keyboard_module.Key, name)

        raise RuntimeError(f"지원하지 않는 키 입력입니다: {key}")


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
