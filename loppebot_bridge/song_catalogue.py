"""Song catalogue handling for DJMAX automation."""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class SongEntry:
    """Represents a song entry loaded from 곡순서.csv."""

    index: int
    title_number: str
    title: str
    normalized_title: str
    leading_letter: str


@dataclass(frozen=True)
class NavigationPlan:
    """Instructions for navigating to a song within DJMAX."""

    song: SongEntry
    letter: str
    offset_from_letter_start: int


def _normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower().replace("&", "and")
    normalized = re.sub(r"[^0-9a-z]+", "", normalized)
    return normalized


def _leading_letter(value: str) -> str:
    for ch in value:
        if ch.isalpha():
            return ch
    return ""


class SongCatalogue:
    """In-memory representation of the DJMAX song order."""

    _TITLE_CANDIDATES: Iterable[str] = (
        "title",
        "곡명",
        "name",
        "song",
    )
    _NUMBER_CANDIDATES: Iterable[str] = (
        "title_number",
        "titlenumber",
        "번호",
        "id",
        "index",
        "no",
    )

    def __init__(self, csv_path: Path):
        self.csv_path = Path(csv_path)
        self.entries: List[SongEntry] = []
        self._title_map: Dict[str, SongEntry] = {}
        self._number_map: Dict[str, SongEntry] = {}
        self._letter_offsets: Dict[str, int] = {}
        self.reload()

    # ------------------------------------------------------------------
    # Data loading
    def reload(self) -> None:
        if not self.csv_path.is_file():
            raise FileNotFoundError(f"곡순서 파일을 찾을 수 없습니다: {self.csv_path}")

        with self.csv_path.open("r", encoding="utf-8-sig") as fp:
            reader = csv.DictReader(fp)
            fieldnames = [name.lower() for name in reader.fieldnames or []]

            title_key = self._resolve_key(fieldnames, self._TITLE_CANDIDATES)
            number_key = self._resolve_key(fieldnames, self._NUMBER_CANDIDATES)

            if not title_key:
                raise ValueError("곡순서.csv 파일에서 곡 제목을 찾지 못했습니다. 헤더를 확인해주세요.")

            self.entries.clear()
            self._title_map.clear()
            self._number_map.clear()
            self._letter_offsets.clear()

            for index, row in enumerate(reader):
                # Normalize keys to lowercase for easier lookup.
                normalized_row = {
                    (k or "").lower(): (v or "")
                    for k, v in row.items()
                    if k is not None
                }
                raw_title = (normalized_row.get(title_key) or "").strip()
                if not raw_title:
                    continue
                title_number = (normalized_row.get(number_key, "").strip() if number_key else str(index + 1))
                normalized_title = _normalize_title(raw_title)
                leading_letter = _leading_letter(normalized_title)

                entry = SongEntry(
                    index=index,
                    title_number=title_number,
                    title=raw_title,
                    normalized_title=normalized_title,
                    leading_letter=leading_letter,
                )
                self.entries.append(entry)
                if normalized_title:
                    self._title_map.setdefault(normalized_title, entry)
                if title_number:
                    self._number_map.setdefault(title_number, entry)
                if leading_letter and leading_letter not in self._letter_offsets:
                    self._letter_offsets[leading_letter] = index

    @staticmethod
    def _resolve_key(fieldnames: Iterable[str], candidates: Iterable[str]) -> Optional[str]:
        lower_map = {name.lower(): name.lower() for name in fieldnames}
        for candidate in candidates:
            key = candidate.lower()
            if key in lower_map:
                return lower_map[key]
        return None

    # ------------------------------------------------------------------
    # Lookup helpers
    def find_song(self, *, title: Optional[str] = None, title_number: Optional[str] = None,
                  fallback_text: Optional[str] = None) -> Optional[SongEntry]:
        if title_number:
            entry = self._number_map.get(str(title_number).strip())
            if entry:
                return entry

        if title:
            normalized = _normalize_title(title)
            entry = self._title_map.get(normalized)
            if entry:
                return entry

        if fallback_text:
            normalized = _normalize_title(fallback_text)
            entry = self._title_map.get(normalized)
            if entry:
                return entry

        # Some cards may include the number as part of the text. Attempt to parse "001. Song" style strings.
        if fallback_text:
            number_match = re.search(r"(\d+)", fallback_text)
            if number_match:
                number = number_match.group(1)
                entry = self._number_map.get(number)
                if entry:
                    return entry

        return None

    def build_navigation_plan(self, song: SongEntry) -> Optional[NavigationPlan]:
        letter = song.leading_letter
        if not letter:
            return None
        letter_offset = self._letter_offsets.get(letter)
        if letter_offset is None:
            return None
        offset = max(0, song.index - letter_offset)
        return NavigationPlan(song=song, letter=letter, offset_from_letter_start=offset)
