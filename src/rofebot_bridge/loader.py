"""Load song definitions from ``곡순서.csv`` files."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterable, List, Mapping, MutableMapping, Optional, Sequence

from .models import Song
from .text_utils import extract_initial_key, split_title_and_number

_LOGGER = logging.getLogger(__name__)


class SongLoadError(RuntimeError):
    """Raised when the CSV file could not be parsed."""


def load_songs(csv_path: Path) -> List[Song]:
    """Load ``Song`` records from *csv_path*.

    The loader is intentionally forgiving: it accepts files with or without a
    header row and tolerates empty lines.
    """

    path = Path(csv_path)
    if not path.exists():
        raise SongLoadError(f"CSV file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))

    if not rows:
        raise SongLoadError(f"CSV file is empty: {path}")

    header = [cell.strip() for cell in rows[0]]
    header_lower = [cell.casefold() for cell in header]
    has_header = any("title" in cell for cell in header_lower)

    songs: List[Song] = []
    if has_header:
        for row in rows[1:]:
            song = _song_from_dict_row(row, header_lower)
            if song:
                songs.append(song)
    else:
        for row in rows:
            song = _song_from_plain_row(row)
            if song:
                songs.append(song)

    if not songs:
        raise SongLoadError(f"No songs could be read from {path}")

    return songs


def _song_from_dict_row(row: Sequence[str], header_lower: Sequence[str]) -> Optional[Song]:
    values: MutableMapping[str, str] = {}
    for key, value in zip(header_lower, row):
        values[key] = value

    title = _get_first(values, ["title", "곡명", "name"])
    if not title:
        return None

    title_number = _get_first(values, ["title_number", "titlenumber", "곡번호", "번호", "id", "no"])
    jump_key = _get_first(values, ["jump_key", "jump", "key", "초성", "initial"])

    if not jump_key:
        jump_key = extract_initial_key(title)

    return Song(title=title, title_number=title_number, jump_key=jump_key)


def _song_from_plain_row(row: Sequence[str]) -> Optional[Song]:
    cleaned = [cell.strip() for cell in row if cell is not None]
    if not cleaned or all(not cell for cell in cleaned):
        return None

    if len(cleaned) == 1:
        number, title = split_title_and_number(cleaned[0])
        if not title:
            title = cleaned[0]
        jump_key = extract_initial_key(title)
        return Song(title=title, title_number=number, jump_key=jump_key)

    title_number = cleaned[0] or None
    title = cleaned[1] if len(cleaned) > 1 else cleaned[0]
    jump_key = cleaned[2] if len(cleaned) > 2 else None

    if not title:
        return None

    if not jump_key:
        jump_key = extract_initial_key(title)

    return Song(title=title, title_number=title_number, jump_key=jump_key)


def _get_first(mapping: Mapping[str, str], keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        if key in mapping and mapping[key].strip():
            return mapping[key].strip()
    return None


__all__ = ["load_songs", "SongLoadError"]
