"""Configuration helpers for the 로페봇 ↔ DJMAX bridge."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

DEFAULT_CONFIG_NAME = "config.json"
EXAMPLE_CONFIG_NAME = "config.example.json"


class ConfigError(RuntimeError):
    """Raised when the runtime configuration cannot be loaded."""


def _candidate_config_paths() -> Iterable[Path]:
    base_dir = Path(__file__).resolve().parent.parent
    # When packaged with PyInstaller the temporary extraction directory is stored in _MEIPASS.
    if hasattr(sys, "_MEIPASS"):
        base = Path(getattr(sys, "_MEIPASS"))
        yield base / DEFAULT_CONFIG_NAME
    # Configuration placed next to the executable has priority.
    yield Path.cwd() / DEFAULT_CONFIG_NAME
    # Fallback to repository-level configuration when running from source.
    yield base_dir / DEFAULT_CONFIG_NAME
    # Finally, allow running directly with the example configuration for quick tests.
    yield base_dir / EXAMPLE_CONFIG_NAME


def load_config() -> Tuple[Dict[str, Any], Path]:
    """Load the JSON configuration file.

    Returns the parsed configuration dictionary and the path it was loaded from.
    """

    for candidate in _candidate_config_paths():
        if candidate.is_file():
            with candidate.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            return data, candidate
    raise ConfigError(
        "구동을 위한 config.json 파일을 찾지 못했습니다. config.example.json을 복사해 "
        "사용자 환경에 맞게 수정해주세요."
    )


def resolve_path(value: str, *, relative_to: Path) -> Path:
    """Resolve a potentially relative path using the configuration file location."""

    path = Path(value)
    if not path.is_absolute():
        path = (relative_to / path).resolve()
    return path
