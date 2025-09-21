"""pywebview application wiring for the 로페봇 bridge."""

from __future__ import annotations

import json
from typing import Any, Dict

import webview

from .djmax_controller import DJMaxController
from .webview_js import INJECT_SCRIPT_TEMPLATE


class BridgeAPI:
    """Exposes Python functions to the injected JavaScript environment."""

    def __init__(self, controller: DJMaxController):
        self.controller = controller

    def select_track(self, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = payload or {}
        return self.controller.select_track(payload)


class WebViewApp:
    def __init__(self, controller: DJMaxController, config: Dict[str, Any]):
        self.controller = controller
        self.config = config
        self.window: webview.Window | None = None
        self.api = BridgeAPI(controller)

    def run(self) -> None:
        url = self.config.get("web_url", "https://b300.vercel.app")
        title = self.config.get("window_caption", "로페봇 연동")
        debug = bool(self.config.get("debug", False))

        self.window = webview.create_window(title, url=url, js_api=self.api, confirm_close=True)
        webview.start(self._on_ready, self.window, debug=debug)

    # ------------------------------------------------------------------
    def _on_ready(self) -> None:
        if not self.window:
            return
        script = self._build_injection_script()
        if script:
            self.window.evaluate_js(script)

    def _build_injection_script(self) -> str:
        script = INJECT_SCRIPT_TEMPLATE
        replacements = {
            "__TILE_SELECTOR__": json.dumps(self.config.get(
                "tile_selector",
                "[data-song-title], [data-title], .tile, .song-card, .loppe-card"
            )),
            "__TITLE_ATTRIBUTE__": json.dumps(self.config.get("title_attribute", "data-song-title")),
            "__FALLBACK_SELECTOR__": json.dumps(self.config.get("title_fallback_selector", ".title, .name")),
            "__NUMBER_ATTRIBUTE__": json.dumps(self.config.get("title_number_attribute", "data-title-number")),
            "__DATASET_KEYS__": json.dumps(self.config.get(
                "dataset_title_number_keys",
                ["titleNumber", "titlenumber", "title-number", "songId", "songid"]
            )),
            "__MENU_TEXT__": json.dumps(self.config.get("context_menu_text", "DJMAX으로 보내기")),
            "__TOAST_DURATION__": str(int(self.config.get("toast_duration_ms", 2600))),
            "__HIGHLIGHT_CLASS__": json.dumps(self.config.get("highlight_class", "loppe-bridge-highlight")),
        }
        for placeholder, value in replacements.items():
            script = script.replace(placeholder, value)
        return script
