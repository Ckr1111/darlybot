"""Entry point for the desktop helper application."""
from __future__ import annotations

import argparse
import contextlib
import logging
import sys
import webbrowser
from importlib import resources
from pathlib import Path
from typing import Iterable, Optional

try:  # pragma: no cover - optional dependency during tests
    import pystray
    from PIL import Image
except ImportError:  # pragma: no cover - gracefully fall back when unavailable
    pystray = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]

from .default_songs import DEFAULT_SONG_CSV
from .input_controller import DJMaxInputController, SimulatedInputController
from .navigator import SongNavigator
from .server import SongServer
from .song_index import SongIndex

_DEFAULT_PORT = 8972
_LOPEBOT_URL = "https://b300.vercel.app"
_TRAY_ICON_FILE = "icon.ico"


def _load_tray_icon_image() -> "Image.Image":
    if Image is None:
        raise RuntimeError("Pillow이(가) 설치되어 있지 않아 트레이 아이콘을 불러올 수 없습니다.")

    with resources.files(__package__).joinpath(_TRAY_ICON_FILE).open("rb") as fp:
        image = Image.open(fp)
        try:
            return image.convert("RGBA")
        finally:
            image.close()


def _open_lopebot_page() -> None:
    try:
        webbrowser.open(_LOPEBOT_URL, new=0, autoraise=True)
    except Exception as exc:  # pragma: no cover - user environment dependent
        logging.getLogger(__name__).warning("로페봇 페이지를 여는 데 실패했습니다: %s", exc)


def _create_tray_icon(server: SongServer) -> "Optional[pystray.Icon]":
    logger = logging.getLogger(__name__)

    if pystray is None or Image is None:
        logger.warning("pystray 또는 Pillow를 사용할 수 없어 트레이 아이콘을 비활성화합니다.")
        return None

    try:
        image = _load_tray_icon_image()
    except Exception as exc:  # pragma: no cover - resource loading failure
        logger.warning("트레이 아이콘 이미지를 불러오지 못했습니다: %s", exc)
        return None

    def handle_open(_: pystray.Icon, __: pystray.MenuItem) -> None:
        logger.info("로페봇 웹 페이지를 엽니다.")
        _open_lopebot_page()

    def handle_quit(icon: pystray.Icon, __: pystray.MenuItem) -> None:
        logger.info("시스템 트레이에서 종료가 요청되었습니다.")
        server.stop()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("로페봇 접속", handle_open),
        pystray.MenuItem("프로그램 종료", handle_quit, default=True),
    )

    return pystray.Icon("darlybot", image, "Darlybot", menu)


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

    tray_icon = _create_tray_icon(server)

    try:
        if tray_icon is None:
            server.serve_forever()
        else:
            try:
                server.start()
                tray_icon.run()
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # pragma: no cover - tray fallback path
                logging.getLogger(__name__).warning(
                    "트레이 아이콘 실행에 실패하여 기본 모드로 전환합니다: %s", exc
                )
                server.stop()
                tray_icon = None
                server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - graceful shutdown
        logging.info("사용자에 의해 중지되었습니다.")
    finally:
        if tray_icon is not None and getattr(tray_icon, "visible", False):
            with contextlib.suppress(Exception):  # pragma: no cover - best effort cleanup
                tray_icon.stop()
        server.stop()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
