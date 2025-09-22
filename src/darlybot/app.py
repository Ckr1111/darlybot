"""Entry point for the desktop helper application."""
from __future__ import annotations

import argparse
import logging
import sys
import threading
import webbrowser
from importlib import resources
from pathlib import Path
from typing import Iterable, Optional

import pystray
from PIL import Image

from .default_songs import DEFAULT_SONG_CSV
from .input_controller import DJMaxInputController, SimulatedInputController
from .navigator import SongNavigator
from .server import SongServer
from .song_index import SongIndex

_DEFAULT_PORT = 8972
_TRAY_TITLE = "Darlybot Helper"
_LOPEBOT_URL = "https://b300.vercel.app"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="darlybot",
        description=(
            "로페봇을 통해 DJMAX RESPECT V의 검색을 자동화하는 도우미입니다."
        ),
    )
    parser.add_argument("--csv", type=Path, help="곡순서.csv 파일의 위치")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP 서버 호스트")
    parser.add_argument(
        "--port",
        default=_DEFAULT_PORT,
        type=int,
        help=f"HTTP 서버 포트 (기본값: {_DEFAULT_PORT})",
    )
    parser.add_argument(
        "--window-title",
        default="DJMAX RESPECT V",
        help="포커스를 가져올 게임 창",
    )
    parser.add_argument(
        "--activation-delay",
        default=0.3,
        type=float,
        help="창을 활성화한 후 대기 시간 (초)",
    )
    parser.add_argument(
        "--key-delay",
        default=0.08,
        type=float,
        help="각 키 입력 사이의 대기 시간 (초)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="키 입력을 실제로 전송하지 않고 API 만 노출",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="로그 레벨",
    )
    return parser


def resolve_csv_path(explicit: Optional[Path]) -> Optional[Path]:
    if explicit:
        return explicit

    candidates = []
    base_candidates: Iterable[Path]

    if getattr(sys, "frozen", False):  # PyInstaller 등으로 패키징된 경우
        exe_dir = Path(sys.executable).resolve().parent
        base_candidates = [exe_dir]
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            base_candidates = list(base_candidates) + [Path(meipass)]
    else:
        module_dir = Path(__file__).resolve().parent
        base_candidates = [Path.cwd(), module_dir, module_dir.parent]

    for base in base_candidates:
        candidates.append(base / "곡순서.csv")
        candidates.append(base / "data" / "곡순서.csv")

    seen = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if path.exists():
            logging.getLogger(__name__).info("곡순서.csv 위치: %s", path)
            return path

    return None


def _load_tray_icon_image() -> Image.Image:
    with resources.as_file(resources.files(__package__) / "icon.ico") as icon_path:
        with Image.open(icon_path) as source:
            return source.convert("RGBA")


def _start_tray_icon(
    server: SongServer, shutdown_event: threading.Event
) -> Optional[pystray.Icon]:
    logger = logging.getLogger(__name__)

    try:
        image = _load_tray_icon_image()
    except FileNotFoundError:
        logger.warning("트레이 아이콘 파일을 찾을 수 없어 시스템 트레이를 비활성화합니다.")
        return None
    except OSError as exc:
        logger.warning("트레이 아이콘을 불러오지 못했습니다: %s", exc)
        return None

    def _open_lopebot(_: pystray.Icon, __: pystray.MenuItem) -> None:
        webbrowser.open(_LOPEBOT_URL, new=0, autoraise=True)

    def _quit(icon: pystray.Icon, __: pystray.MenuItem) -> None:
        shutdown_event.set()
        server.stop()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("로페봇 접속", _open_lopebot),
        pystray.MenuItem("프로그램 종료", _quit),
    )

    try:
        icon = pystray.Icon("darlybot", image, _TRAY_TITLE, menu)
    except Exception as exc:  # pragma: no cover - backend specific failures
        logger.warning("시스템 트레이 아이콘을 초기화하지 못했습니다: %s", exc)
        return None

    icon.run_detached()
    return icon


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="[%(levelname)s] %(message)s",
    )

    csv_path = resolve_csv_path(args.csv)
    if csv_path is not None:
        try:
            index = SongIndex(csv_path)
        except FileNotFoundError as exc:
            parser.error(str(exc))
            return 2
    else:
        logging.getLogger(__name__).info("내장된 곡순서.csv 데이터를 사용합니다.")
        index = SongIndex.from_csv_text(
            DEFAULT_SONG_CSV,
            name="embedded 곡순서.csv",
        )
    if args.dry_run:
        controller = SimulatedInputController()
        logging.info("드라이런 모드로 실행 중입니다. 키 입력은 전송되지 않습니다.")
    else:
        controller = DJMaxInputController(
            window_title=args.window_title,
            activation_delay=args.activation_delay,
            key_delay=args.key_delay,
        )

    navigator = SongNavigator(index, controller)
    server = SongServer(
        navigator,
        index=index,
        host=args.host,
        port=args.port,
    )

    shutdown_event = threading.Event()
    tray_icon: Optional[pystray.Icon] = None

    try:
        server.start()
        tray_icon = _start_tray_icon(server, shutdown_event)
        while server.is_running():
            if shutdown_event.wait(0.5):
                break
    except KeyboardInterrupt:  # pragma: no cover - graceful shutdown
        logging.info("사용자에 의해 중지되었습니다.")
        shutdown_event.set()
    finally:
        server.stop()
        if tray_icon is not None:
            tray_icon.stop()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
