"""Command-line entry point for the Lopebot DJMAX bridge."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .controller import DJMaxController
from .navigator import SongNavigator

if TYPE_CHECKING:  # pragma: no cover - only for type hints
    from .server import create_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bridge Lopebot with DJMAX RESPECT V")
    parser.add_argument("--csv", type=Path, default=Path("곡순서.csv"), help="Path to the song order CSV file")
    parser.add_argument("--host", default="127.0.0.1", help="Host/IP to bind the local server")
    parser.add_argument("--port", type=int, default=8731, help="Port to bind the local server")
    parser.add_argument("--window-title", default="DJMAX RESPECT V", help="Title of the DJMAX window")
    parser.add_argument("--key-delay", type=float, default=0.05, help="Delay between arrow key presses (seconds)")
    parser.add_argument("--jump-delay", type=float, default=0.2, help="Delay after jumping to a letter group (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="Do not send keyboard input; log only")
    parser.add_argument("--allow-origin", default="*", help="Value for Access-Control-Allow-Origin header")
    parser.add_argument("--log-level", default="INFO", help="Logging level (e.g. INFO, DEBUG)")
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Optional path to a log file (recommended when running as a background task)",
    )
    return parser.parse_args()


def configure_logging(level: str, log_file: Path | None) -> None:
    """Initialise application logging for console or background execution."""

    log_level = getattr(logging, level.upper(), logging.INFO)
    handlers: list[logging.Handler] = []

    if log_file:
        log_file = log_file.expanduser()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    else:
        stream = getattr(sys, "stderr", None)
        if stream is None:
            fallback = Path.cwd() / "darlybot.log"
            fallback.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(fallback, encoding="utf-8"))
        else:
            handlers.append(logging.StreamHandler(stream))

    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level, args.log_file)
    logger = logging.getLogger("darlybot")

    try:
        from aiohttp import web
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        logger.error("aiohttp 패키지가 필요합니다. 'pip install aiohttp' 명령으로 설치한 뒤 다시 실행하세요.")
        raise SystemExit(2) from exc

    from .server import create_app

    try:
        navigator = SongNavigator(args.csv)
    except Exception as exc:  # pragma: no cover - configuration error
        logger.error("Failed to load song list: %s", exc)
        raise SystemExit(2) from exc

    controller = DJMaxController(
        args.window_title,
        key_delay=args.key_delay,
        jump_delay=args.jump_delay,
        dry_run=args.dry_run,
    )

    app = create_app(navigator, controller, allow_origin=args.allow_origin)
    logger.info("Starting bridge server on %s:%s (dry_run=%s)", args.host, args.port, controller.dry_run)
    web.run_app(app, host=args.host, port=args.port)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
