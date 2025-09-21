"""Utilities for mapping Lopebot song titles to keyboard navigation plans."""

from __future__ import annotations

import csv
import logging
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Song:
    """A single song entry in the DJMAX RESPECT V song list."""

    index: int
    title: str
    normalized_title: str
    initial_letter: Optional[str]


@dataclass(frozen=True)
class NavigationPlan:
    """Plan describing how to reach a given song via keyboard navigation."""

    title: str
    letter: Optional[str]
    offset: int

    def keystrokes(self) -> List[str]:
        """Return the sequence of keystrokes needed to reach the song."""

        keys: List[str] = []
        if self.letter:
            keys.append(self.letter)
        direction = "down" if self.offset >= 0 else "up"
        for _ in range(abs(self.offset)):
            keys.append(direction)
        return keys

    def to_dict(self) -> Dict[str, object]:
        """Serialise the plan as a JSON-compatible dictionary."""

        return {
            "title": self.title,
            "letter": self.letter,
            "offset": self.offset,
            "keystrokes": self.keystrokes(),
        }


class SongNavigator:
    """Load song metadata and generate navigation plans for DJMAX RESPECT V."""

    def __init__(self, csv_path: Path | str, *, encoding: str = "utf-8-sig") -> None:
        self.csv_path = Path(csv_path)
        self.encoding = encoding
        self._songs: List[Song] = []
        self._index_by_normalized: Dict[str, int] = {}
        self._first_index_by_letter: Dict[str, int] = {}
        self._load()

    @property
    def songs(self) -> Sequence[Song]:
        """Return the loaded songs in order."""

        return self._songs

    @property
    def song_titles(self) -> List[str]:
        """Return the original song titles."""

        return [song.title for song in self._songs]

    @property
    def available_letters(self) -> List[str]:
        """Return the letters that have at least one song."""

        return sorted(self._first_index_by_letter.keys())

    @property
    def song_count(self) -> int:
        return len(self._songs)

    def plan_for_title(self, title: str) -> NavigationPlan:
        """Return the navigation plan for the provided song title."""

        normalized = self._normalize_title(title)
        if normalized not in self._index_by_normalized:
            raise KeyError(f"Song '{title}' was not found in {self.csv_path.name}.")

        index = self._index_by_normalized[normalized]
        song = self._songs[index]
        if song.initial_letter:
            start_index = self._first_index_by_letter[song.initial_letter]
        else:
            # Songs without an alphabetical initial are reached relative to their position.
            start_index = index
        offset = index - start_index
        return NavigationPlan(title=song.title, letter=song.initial_letter, offset=offset)

    def _load(self) -> None:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Song list CSV not found: {self.csv_path}")

        songs: List[Song] = []
        index_map: Dict[str, int] = {}
        first_letter_map: Dict[str, int] = {}

        with self.csv_path.open("r", encoding=self.encoding, newline="") as file:
            reader = csv.reader(file)
            for index, row in enumerate(reader):
                if not row:
                    continue
                title = row[0].strip()
                if index == 0 and title.lower() in {"title", "곡명"} and len(row) == 1:
                    logger.debug("Skipping header row: %s", row)
                    continue
                if not title:
                    continue
                normalized = self._normalize_title(title)
                if normalized in index_map:
                    logger.warning("Duplicate song title detected in CSV: '%s'", title)
                    continue
                letter = self._initial_letter(title)
                song = Song(index=len(songs), title=title, normalized_title=normalized, initial_letter=letter)
                songs.append(song)
                index_map[normalized] = song.index
                if letter and letter not in first_letter_map:
                    first_letter_map[letter] = song.index

        if not songs:
            raise ValueError(f"No songs were loaded from {self.csv_path}")

        self._songs = songs
        self._index_by_normalized = index_map
        self._first_index_by_letter = first_letter_map

        logger.info(
            "Loaded %s songs from %s (%s letters)",
            len(self._songs),
            self.csv_path,
            len(self._first_index_by_letter),
        )

    @staticmethod
    def _normalize_title(title: str) -> str:
        normalized = unicodedata.normalize("NFKC", title)
        normalized = normalized.strip().casefold()
        # Collapse multiple spaces for reliable comparisons.
        normalized = " ".join(normalized.split())
        return normalized

    @staticmethod
    def _initial_letter(title: str) -> Optional[str]:
        for char in unicodedata.normalize("NFKC", title):
            if not char.isalpha():
                continue
            upper = char.upper()
            if "A" <= upper <= "Z":
                return upper.lower()
        return None


__all__ = ["Song", "SongNavigator", "NavigationPlan"]
