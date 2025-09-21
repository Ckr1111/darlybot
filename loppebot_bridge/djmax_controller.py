"""Logic responsible for sending keystrokes to DJMAX RESPECT V."""

from __future__ import annotations

import importlib
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable

from .song_catalogue import NavigationPlan, SongCatalogue


class DJMaxWindowNotFoundError(RuntimeError):
    """Raised when the DJMAX game window is not available."""


@dataclass
class ControllerSettings:
    window_titles: Iterable[str]
    press_enter: bool
    key_press_interval: float
    down_press_interval: float
    activate_window_pause: float


class DJMaxController:
    """Bridge between 로페봇 events and DJMAX keystrokes."""

    def __init__(self, config: Dict[str, Any], catalogue: SongCatalogue):
        self.catalogue = catalogue
        self.config = config
        self._lock = threading.Lock()
        self._pyautogui = None
        self._pygetwindow = None
        self.settings = self._build_settings(config)
        self._import_libraries()

    # ------------------------------------------------------------------
    def _build_settings(self, config: Dict[str, Any]) -> ControllerSettings:
        window_titles = config.get("window_title_candidates")
        if not window_titles:
            default_title = config.get("window_title", "DJMAX RESPECT V")
            window_titles = [default_title]
        elif isinstance(window_titles, str):
            window_titles = [window_titles]

        return ControllerSettings(
            window_titles=tuple(window_titles),
            press_enter=bool(config.get("press_enter", False)),
            key_press_interval=float(config.get("key_press_interval", 0.08)),
            down_press_interval=float(config.get("down_press_interval", 0.05)),
            activate_window_pause=float(config.get("activate_window_pause", 0.35)),
        )

    def _import_libraries(self) -> None:
        try:
            self._pyautogui = importlib.import_module("pyautogui")
            self._pygetwindow = importlib.import_module("pygetwindow")
        except Exception as exc:  # pragma: no cover - depends on host platform
            raise RuntimeError(
                "pyautogui 및 pygetwindow 모듈이 필요합니다. requirements.txt를 참고하여 설치해주세요."
            ) from exc
        self._pyautogui.FAILSAFE = False

    # ------------------------------------------------------------------
    def select_track(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Locate a song based on payload information and issue keystrokes."""

        with self._lock:
            song = self._match_song(payload)
            if not song:
                return {
                    "status": "error",
                    "message": "곡 정보를 찾을 수 없습니다. 곡순서.csv 파일을 확인해주세요.",
                }

            plan = self.catalogue.build_navigation_plan(song)
            if not plan:
                return {
                    "status": "error",
                    "message": f"{song.title} 곡으로 이동하기 위한 키를 계산할 수 없습니다.",
                }

            try:
                self._apply_navigation_plan(plan)
            except DJMaxWindowNotFoundError as exc:
                return {"status": "error", "message": str(exc)}

            message = f"{song.title} (#{song.title_number}) 이동 키 입력 완료"
            return {"status": "ok", "message": message, "plan": {
                "letter": plan.letter,
                "down": plan.offset_from_letter_start,
            }}

    # ------------------------------------------------------------------
    def _match_song(self, payload: Dict[str, Any]):
        title_number = (
            payload.get("titleNumber")
            or payload.get("title_number")
            or payload.get("number")
            or payload.get("id")
        )
        title = payload.get("title") or payload.get("name")
        fallback_text = payload.get("text") or payload.get("rawText")
        return self.catalogue.find_song(title=title, title_number=title_number, fallback_text=fallback_text)

    def _apply_navigation_plan(self, plan: NavigationPlan) -> None:
        window = self._focus_window()
        # Allow the OS a small moment to switch focus.
        time.sleep(self.settings.activate_window_pause)

        letter = plan.letter.lower()
        self._pyautogui.press(letter)
        if plan.offset_from_letter_start:
            time.sleep(self.settings.key_press_interval)
            for _ in range(plan.offset_from_letter_start):
                self._pyautogui.press("down")
                time.sleep(self.settings.down_press_interval)

        if self.settings.press_enter:
            time.sleep(self.settings.key_press_interval)
            self._pyautogui.press("enter")

    def _focus_window(self):
        for title in self.settings.window_titles:
            windows = self._pygetwindow.getWindowsWithTitle(title)
            for window in windows:
                try:
                    if window.isMinimized:
                        window.restore()
                        time.sleep(0.2)
                    window.activate()
                    # Give the system a moment to update window states.
                    for _ in range(5):
                        time.sleep(0.1)
                        if window.isActive:
                            return window
                except Exception:
                    continue
        raise DJMaxWindowNotFoundError("DJMAX RESPECT V 실행 중인지 확인해주세요.")
