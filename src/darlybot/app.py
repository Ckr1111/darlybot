"""Entry point for the desktop helper application."""
from __future__ import annotations

import argparse
import logging
import sys
import webbrowser
from pathlib import Path
from typing import Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported for type checkers only
    from PIL import Image
    from pystray import Icon, MenuItem

from .default_songs import DEFAULT_SONG_CSV
from .input_controller import DJMaxInputController, SimulatedInputController
from .navigator import SongNavigator
from .server import SongServer
from .song_index import SongIndex

_DEFAULT_PORT = 8972
_LOPEBOT_URL = "https://b300.vercel.app/"
_TRAY_ICON_NAME = "darlybot"

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
    tray_group = parser.add_mutually_exclusive_group()
    tray_group.add_argument(
        "--tray",
        dest="tray",
        action="store_true",
        help="시스템 트레이 아이콘을 표시합니다.",
    )
    tray_group.add_argument(
        "--no-tray",
        dest="tray",
        action="store_false",
        help="시스템 트레이 아이콘을 표시하지 않습니다.",
    )
    parser.set_defaults(tray=None)
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
            _LOGGER.info("곡순서.csv 위치: %s", path)
            return path

    return None


def resolve_icon_path(filename: str = "favicon.ico") -> Optional[Path]:
    """Return the path to the tray icon, if available."""

    candidates: list[Path] = []
    if getattr(sys, "frozen", False):  # PyInstaller 등으로 패키징된 경우
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / filename)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / filename)

    module_dir = Path(__file__).resolve().parent
    candidates.extend(
        [
            module_dir / filename,
            module_dir.parent / filename,
            Path.cwd() / filename,
        ]
    )

    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except FileNotFoundError:  # pragma: no cover - platform dependent
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        _LOGGER.debug("트레이 아이콘 후보: %s", resolved)
        if resolved.exists():
            _LOGGER.info("트레이 아이콘 사용: %s", resolved)
            return resolved
    return None


def _hide_console_window() -> None:
    """Hide the console window on Windows builds."""

    if not sys.platform.startswith("win"):
        return
    try:  # pragma: no cover - requires Windows console
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:  # pragma: no cover - defensive
        _LOGGER.debug("콘솔 창을 숨기는 데 실패했습니다.", exc_info=True)


class _TrayApplication:
    """Manage the lifecycle of the system tray icon."""

    def __init__(self, server: SongServer, icon_path: Path) -> None:
        self._server = server
        from PIL import Image  # Imported lazily for headless environments
        import pystray

        with Image.open(icon_path) as image:
            self._image: Image.Image = image.copy()

        open_item = pystray.MenuItem("로페봇 접속", self._open_lopebot, default=True)
        exit_item = pystray.MenuItem("끄기", self._shutdown)
        self._menu = pystray.Menu(open_item, exit_item)
        self._icon = pystray.Icon(
            _TRAY_ICON_NAME,
            self._image,
            "Darlybot Helper",
            menu=self._menu,
        )

    def run(self) -> None:
        self._icon.run(setup=self._on_ready)

    def _on_ready(self, icon: "Icon") -> None:
        icon.visible = True
        _LOGGER.info("시스템 트레이 아이콘이 준비되었습니다.")

    def _open_lopebot(self, icon: "Icon", item: "MenuItem") -> None:
        _LOGGER.info("로페봇을 브라우저에서 엽니다: %s", _LOPEBOT_URL)
        webbrowser.open_new_tab(_LOPEBOT_URL)

    def _shutdown(self, icon: "Icon", item: "MenuItem") -> None:
        _LOGGER.info("사용자 요청으로 애플리케이션을 종료합니다.")
        self._server.stop()
        icon.visible = False
        icon.stop()


def _run_with_tray(server: SongServer, icon_path: Path) -> int:
    _hide_console_window()

    try:
        server.start()
    except OSError as exc:
        _LOGGER.error("HTTP 서버를 시작하지 못했습니다: %s", exc)
        return 1

    tray = _TrayApplication(server, icon_path)
    exit_code = 0
    try:
        tray.run()
    except KeyboardInterrupt:  # pragma: no cover - defensive
        _LOGGER.info("사용자에 의해 중지되었습니다.")
        exit_code = 0
    except Exception:  # pragma: no cover - UI stacktrace
        _LOGGER.exception("시스템 트레이 아이콘 실행 중 오류가 발생했습니다.")
        exit_code = 1
    finally:
        server.stop()

    return exit_code


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
        _LOGGER.info("내장된 곡순서.csv 데이터를 사용합니다.")
        index = SongIndex.from_csv_text(
            DEFAULT_SONG_CSV,
            name="embedded 곡순서.csv",
        )
    if args.dry_run:
        controller = SimulatedInputController()
        _LOGGER.info("드라이런 모드로 실행 중입니다. 키 입력은 전송되지 않습니다.")
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

    tray_preference = args.tray
    if tray_preference is None:
        tray_preference = getattr(sys, "frozen", False)

    if tray_preference:
        icon_path = resolve_icon_path()
        if icon_path is None:
            _LOGGER.error("favicon.ico 아이콘을 찾을 수 없습니다. --no-tray 옵션으로 실행해 주세요.")
            return 1
        return _run_with_tray(server, icon_path)

    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - graceful shutdown
        _LOGGER.info("사용자에 의해 중지되었습니다.")
    finally:
        server.stop()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
