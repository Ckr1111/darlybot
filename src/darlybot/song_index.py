"""Utilities for loading and working with the song order CSV file."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Sequence, Tuple
import csv
import unicodedata

__all__ = [
    "SongEntry",
    "SongIndex",
    "SongNotFoundError",
    "SongIndexError",
    "SCROLL_UP_KEY",
    "SCROLL_DOWN_KEY",
]

SCROLL_UP_KEY = "scroll_up"
SCROLL_DOWN_KEY = "scroll_down"


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

    #: Logical letter name used for titles that start with a Hangul character.
    _HANGUL_LETTER = "한글"

    #: Logical letter name used for titles that start with digits or symbols.
    _SYMBOL_LETTER = "특수문자"

    #: Initial key sequences associated with each non-alphabet bucket.
    _HANGUL_BASE_PREFIX: Tuple[str, ...] = ("a",)
    _SYMBOL_PREFIX: Tuple[str, ...] = ("a", "pagedown")

    def __init__(self, csv_path: Path | str):
        self.csv_path = Path(csv_path)
        self._entries: List[SongEntry] = []
        self._by_number: Dict[str, SongEntry] = {}
        self._by_title: Dict[str, SongEntry] = {}
        self._first_index_by_letter: Dict[str, int] = {}
        self._prefix_keys_by_letter: Dict[str, Sequence[str]] = {}
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

        The sequence begins with the shortcut needed to jump to the correct
        bucket (for example the lowercase letter for ``A~Z`` titles or the
        ``a`` + mouse wheel / ``pagedown`` combination for 한글 및 특수문자 곡).
        The remaining keys are ``'up'`` or ``'down'`` presses that move from
        the bucket's first song to the desired entry.
        """

        try:
            prefix = list(self._prefix_keys_by_letter[entry.letter])
        except KeyError as exc:  # pragma: no cover - defensive mapping lookup
            raise SongIndexError(
                f"'{entry.letter}' 그룹의 초깃값을 찾을 수 없습니다. 곡순서.csv 를 확인해주세요."
            ) from exc

        letter_index = self.letter_anchor(entry.letter)
        offset = entry.index - letter_index
        if offset < 0:
            arrow = SCROLL_UP_KEY
        else:
            arrow = SCROLL_DOWN_KEY
        steps = prefix
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
                letter, prefix = self._derive_anchor(title)
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
                self._prefix_keys_by_letter.setdefault(letter, prefix)

        self._finalise_special_prefixes()

    def _derive_anchor(self, title: str) -> Tuple[str, Tuple[str, ...]]:
        for char in self._iter_significant_chars(title):
            if char.isascii() and char.isalpha():
                lower = char.lower()
                return char.upper(), (lower,)
            if self._is_hangul(char):
                return self._HANGUL_LETTER, self._HANGUL_BASE_PREFIX
            return self._SYMBOL_LETTER, self._SYMBOL_PREFIX
        raise SongIndexError(
            f"제목 '{title}' 에서 탐색에 사용할 시작 문자를 찾을 수 없습니다."
        )

    def _finalise_special_prefixes(self) -> None:
        self._finalise_hangul_prefix()

    def _finalise_hangul_prefix(self) -> None:
        letter = self._HANGUL_LETTER
        if letter not in self._first_index_by_letter:
            return

        # The game does not provide a direct shortcut to the Hangul bucket, so
        # we move to the ``A`` section and scroll upwards.  When the dataset
        # does not include any ``A`` titles we keep the base prefix and rely on
        # the caller to provide manual input if necessary.
        hangul_anchor = self._first_index_by_letter[letter]
        ascii_anchor = self._first_index_by_letter.get("A")
        if ascii_anchor is None:
            return

        scroll_steps = max(0, ascii_anchor - hangul_anchor)
        prefix = self._HANGUL_BASE_PREFIX + (SCROLL_UP_KEY,) * scroll_steps
        self._prefix_keys_by_letter[letter] = prefix

    def _iter_significant_chars(self, text: str) -> Iterable[str]:
        for char in text:
            if char.isspace():
                continue
            yield char

    def _is_hangul(self, char: str) -> bool:
        return "HANGUL" in unicodedata.name(char, "")

    def _normalise_text(self, text: str) -> str:
        return unicodedata.normalize("NFKC", text).casefold().strip()
