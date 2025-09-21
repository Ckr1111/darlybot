"""Utilities for loading and working with the song order CSV file."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Sequence
import csv
import unicodedata

__all__ = [
    "SongEntry",
    "SongIndex",
    "SongNotFoundError",
    "SongIndexError",
]


@dataclass(frozen=True)
class SongEntry:
    """Represents a single song row from ``곡순서.csv``."""

    index: int
    title_number: str
    title: str
    letter: str

    def to_payload(self) -> Dict[str, str]:
        """Return a serialisable representation used by the HTTP server."""

        return {
            "index": self.index,
            "title_number": self.title_number,
            "title": self.title,
            "letter": self.letter,
        }


class SongIndexError(RuntimeError):
    """Base error for song index issues."""


class SongNotFoundError(SongIndexError):
    """Raised when a song cannot be found in the loaded CSV."""


class SongIndex:
    """Utility for looking up song indices and computing key sequences.

    The CSV file is expected to contain at least the two columns
    ``title_number`` and ``title``.  Extra columns are ignored but preserved in
    the :class:`SongEntry` instances to make it easy to expose them in the
    integration API.
    """

    #: Characters that should be treated as word separators when deriving the
    #: leading alphabetical key for a title.
    _SEPARATORS: Sequence[str] = tuple("-'\"()[]{}.,/\\|!?: ")

    def __init__(self, csv_path: Path | str):
        self.csv_path = Path(csv_path)
        self._entries: List[SongEntry] = []
        self._by_number: Dict[str, SongEntry] = {}
        self._by_title: Dict[str, SongEntry] = {}
        self._first_index_by_letter: Dict[str, int] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[SongEntry]:
        return iter(self._entries)

    @property
    def entries(self) -> Sequence[SongEntry]:
        return tuple(self._entries)

    def get_by_title_number(self, title_number: str) -> SongEntry:
        try:
            return self._by_number[str(title_number).strip()]
        except KeyError as exc:  # pragma: no cover - trivial mapping lookup
            raise SongNotFoundError(
                f"곡 번호 '{title_number}' 를 곡순서.csv 에서 찾을 수 없습니다."
            ) from exc

    def get_by_title(self, title: str) -> SongEntry:
        key = self._normalise_text(title)
        try:
            return self._by_title[key]
        except KeyError as exc:  # pragma: no cover - trivial mapping lookup
            raise SongNotFoundError(
                f"제목 '{title}' 를 곡순서.csv 에서 찾을 수 없습니다."
            ) from exc

    def letter_anchor(self, letter: str) -> int:
        """Return the index of the first song whose letter matches ``letter``."""

        letter = letter.upper()
        if letter not in self._first_index_by_letter:
            raise SongIndexError(
                f"제목이 '{letter}' 로 시작하는 곡의 첫 위치를 찾을 수 없습니다."
            )
        return self._first_index_by_letter[letter]

    # Key calculation ---------------------------------------------------
    def key_sequence_for(self, entry: SongEntry) -> List[str]:
        """Return the sequence of keys required to reach ``entry``.

        The first key will always be the alphabetical letter derived from the
        title (in lower-case to match the in-game behaviour).  The rest of the
        sequence is a series of ``'up'`` or ``'down'`` key presses that move
        from the first song for that letter to the desired entry.
        """

        letter_index = self.letter_anchor(entry.letter)
        offset = entry.index - letter_index
        if offset < 0:
            arrow = "up"
        else:
            arrow = "down"
        steps = [entry.letter.lower()]
        for _ in range(abs(offset)):
            steps.append(arrow)
        return steps

    # ------------------------------------------------------------------
    # Internal helpers
    def _load(self) -> None:
        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"곡순서.csv 파일을 찾을 수 없습니다: {self.csv_path}"
            )

        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames:
                raise SongIndexError(
                    "곡순서.csv 파일에 헤더가 없습니다. 'title_number,title' 형식을 사용하세요."
                )
            headers = {name.lower(): name for name in reader.fieldnames}
            if "title_number" not in headers or "title" not in headers:
                raise SongIndexError(
                    "곡순서.csv 파일은 'title_number' 와 'title' 헤더를 포함해야 합니다."
                )

            title_number_key = headers["title_number"]
            title_key = headers["title"]

            for row in reader:
                title_number = str(row.get(title_number_key, "")).strip()
                title = str(row.get(title_key, "")).strip()
                if not title:
                    # Skip completely empty rows to make editing easier.
                    continue
                letter = self._derive_letter(title)
                entry = SongEntry(
                    index=len(self._entries),
                    title_number=title_number,
                    title=title,
                    letter=letter,
                )
                self._entries.append(entry)
                if title_number:
                    self._by_number[title_number] = entry
                self._by_title[self._normalise_text(title)] = entry
                self._first_index_by_letter.setdefault(letter, entry.index)

    def _derive_letter(self, title: str) -> str:
        for char in self._iter_alpha_chars(title):
            return char.upper()
        raise SongIndexError(
            f"제목 '{title}' 에서 알파벳 시작 문자를 찾을 수 없습니다."
        )

    def _iter_alpha_chars(self, text: str) -> Iterable[str]:
        for char in text:
            if char in self._SEPARATORS:
                continue
            category = unicodedata.category(char)
            if category.startswith("L") and char.encode("ascii", "ignore"):
                yield char

    def _normalise_text(self, text: str) -> str:
        return unicodedata.normalize("NFKC", text).casefold().strip()
