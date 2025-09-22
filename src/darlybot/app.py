"""Entry point for the desktop helper application."""
from __future__ import annotations

import argparse
import contextlib
import logging
import sys
import threading
import webbrowser
from importlib import resources
from io import BytesIO
from pathlib import Path
from typing import Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from PIL import Image

from .default_songs import DEFAULT_SONG_CSV
from .input_controller import DJMaxInputController, SimulatedInputController
from .navigator import SongNavigator
from .server import SongServer
from .song_index import SongIndex

_DEFAULT_PORT = 8972
_TRAY_WEB_URL = "https://b300.vercel.app"
_PACKAGE_NAME = __package__ or "darlybot"
_LOGGER = logging.getLogger(__name__)


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


def _load_tray_image() -> "Image.Image":
    """Load the tray icon bundled with the package."""

    from PIL import Image  # Imported lazily to keep startup fast.

    data = resources.files(_PACKAGE_NAME).joinpath("icon.ico").read_bytes()
    with BytesIO(data) as stream:
        with Image.open(stream) as image:
            return image.copy()


def _run_with_tray(server: SongServer) -> bool:
    """Run the application with a system tray icon if possible.

    Returns ``True`` when the tray loop completed (for example, when the user
    chose to exit the application from the tray menu).  If the tray icon cannot
    be initialised this function returns ``False`` so the caller can fall back
    to the console-only behaviour.
    """

    try:
        import pystray
    except Exception as exc:  # pragma: no cover - platform dependent
        _LOGGER.warning(
            "트레이 아이콘을 초기화할 수 없어 콘솔 모드로 실행합니다: %s", exc
        )
        return False

    try:
        icon_image = _load_tray_image()
    except Exception as exc:  # pragma: no cover - filesystem dependent
        _LOGGER.warning(
            "트레이 아이콘 이미지를 불러올 수 없어 콘솔 모드로 실행합니다: %s", exc
        )
        return False

    stop_event = threading.Event()

    def on_quit(icon: "pystray.Icon", item) -> None:
        _LOGGER.info("트레이 아이콘에서 종료 요청을 받았습니다.")
        stop_event.set()
        icon.visible = False
        icon.stop()

    def on_open_web(icon: "pystray.Icon", item) -> None:
        _LOGGER.info("기본 브라우저에서 %s 를 엽니다.", _TRAY_WEB_URL)
        webbrowser.open(_TRAY_WEB_URL)

    menu = pystray.Menu(
        pystray.MenuItem("웹 열기", on_open_web),
        pystray.MenuItem("닫기", on_quit),
    )
    icon = pystray.Icon("darlybot", icon_image, "Darlybot Helper", menu=menu)

    server.start()
    try:
        icon.run_detached()
    except Exception as exc:  # pragma: no cover - backend dependent
        _LOGGER.warning("트레이 아이콘을 실행하지 못했습니다: %s", exc)
        server.stop()
        return False

    try:
        while not stop_event.wait(0.5):
            pass
    except KeyboardInterrupt:  # pragma: no cover - interactive behaviour
        _LOGGER.info("사용자에 의해 중지되었습니다.")
        stop_event.set()
    finally:
        with contextlib.suppress(Exception):
            icon.visible = False
            icon.stop()
        server.stop()

    return True


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

    if _run_with_tray(server):
        return 0

    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - graceful shutdown
        logging.info("사용자에 의해 중지되었습니다.")
    finally:
        server.stop()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
