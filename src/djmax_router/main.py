"""Entry point for the Ropebot ↔ DJMAX bridge."""
from __future__ import annotations

import argparse
import logging
import signal
import sys
from pathlib import Path

from .csv_loader import SongLibrary
from .djmax_control import DjmaxController
from .server import CommandProcessor, create_server


def _default_csv_path() -> Path:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    options = [
        Path(sys.argv[0]).resolve().parent / "곡순서.csv",
        base_dir / "곡순서.csv",
        Path.cwd() / "곡순서.csv",
    ]
    for path in options:
        if path.exists():
            return path
    return options[0]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ropebot bridge for DJMAX RESPECT V")
    parser.add_argument("--host", default="127.0.0.1", help="Interface to bind the HTTP server to")
    parser.add_argument("--port", type=int, default=47815, help="Port to expose the HTTP server on")
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Path to 곡순서.csv (defaults to alongside the executable).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not send key presses; log only.")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, …)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    csv_path = args.csv or _default_csv_path()
    logging.getLogger(__name__).info("Using song list: %s", csv_path)
    try:
        library = SongLibrary(csv_path)
    except Exception as exc:  # pragma: no cover - runtime guard
        logging.getLogger(__name__).error("Failed to load song library: %s", exc)
        return 1

    controller = DjmaxController(dry_run=args.dry_run)
    processor = CommandProcessor(library, controller)
    server = create_server(args.host, args.port, processor)

    def _handle_stop(signum, frame):  # noqa: ANN001 - required signature
        logging.getLogger(__name__).info("Received signal %s; shutting down.", signum)
        server.shutdown()

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    logging.getLogger(__name__).info("Starting server on %s:%d", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - interactive guard
        logging.getLogger(__name__).info("Interrupted by user; exiting.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
