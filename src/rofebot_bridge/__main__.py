"""Command line entry point for the RofeBot ↔ DJMAX bridge."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, Optional

from . import BridgeServer, DJMaxInputSender, SearchPlanner, SongCatalog, load_songs
from .loader import SongLoadError

_LOG_FORMAT = "[%(levelname)s] %(message)s"
_LOGGER = logging.getLogger(__name__)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="곡순서.csv", help="Path to the 곡순서.csv file")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface for the local HTTP server")
    parser.add_argument("--port", type=int, default=29184, help="Port for the local HTTP server")
    parser.add_argument("--window-title", default="DJMAX RESPECT V", help="Title of the DJMAX window")
    parser.add_argument("--key-delay", type=float, default=0.05, help="Delay between key presses (seconds)")
    parser.add_argument("--focus-delay", type=float, default=0.15, help="Delay after focusing the game window")
    parser.add_argument("--dry-run", action="store_true", help="Do not send keys, only log actions")
    parser.add_argument("--query", help="Send keys for a single song and exit")
    parser.add_argument(
        "--list", dest="list_songs", action="store_true", help="Print the loaded songs and exit"
    )
    parser.add_argument("--log-level", default="INFO", help="Python logging level (DEBUG, INFO, …)")
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)

    logging.basicConfig(level=args.log_level.upper(), format=_LOG_FORMAT)

    csv_path = Path(args.csv)
    try:
        songs = load_songs(csv_path)
    except SongLoadError as exc:
        _LOGGER.error("%s", exc)
        return 2

    catalog = SongCatalog(songs)
    planner = SearchPlanner(catalog)
    sender = DJMaxInputSender(
        window_title=args.window_title,
        key_delay=args.key_delay,
        focus_delay=args.focus_delay,
        dry_run=args.dry_run,
    )

    if args.list_songs:
        for song in catalog.songs:
            label = song.display_label()
            key = song.default_jump_key()
            print(f"{label} (key={key})")
        return 0

    if args.query:
        result = planner.plan_from_query(args.query)
        logging.info(
            "Plan for %s: key=%s offset=%s sequence=%s",
            result.match.song.display_label(),
            result.plan.base_key,
            result.plan.offset,
            result.plan.as_key_sequence(),
        )
        sender.execute_plan(result.plan)
        return 0

    server = BridgeServer(planner=planner, sender=sender, host=args.host, port=args.port)
    server.serve_forever()
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation guard
    raise SystemExit(main())
