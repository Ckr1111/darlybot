"""Entry-point helper for the 로페봇 ↔ DJMAX bridge."""

from __future__ import annotations

from .config_loader import ConfigError, load_config, resolve_path
from .djmax_controller import DJMaxController
from .song_catalogue import SongCatalogue
from .webview_app import WebViewApp


def run_app() -> None:
    """Start the pywebview application."""

    try:
        config, config_path = load_config()
    except ConfigError as exc:
        print(exc)
        raise SystemExit(1) from exc

    csv_path = resolve_path(config.get("csv_path", "곡순서.csv"), relative_to=config_path.parent)

    try:
        catalogue = SongCatalogue(csv_path)
    except Exception as exc:
        print(f"곡순서.csv 로딩에 실패했습니다: {exc}")
        raise SystemExit(1) from exc

    controller = DJMaxController(config, catalogue)
    app = WebViewApp(controller, config)
    app.run()


def main() -> None:
    run_app()


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
