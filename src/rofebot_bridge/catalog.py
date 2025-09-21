"""Song lookup helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .models import Song
from .text_utils import normalize_number, normalize_text, split_title_and_number

_LOGGER = logging.getLogger(__name__)


class SongNotFoundError(LookupError):
    """Raised when the requested song could not be located."""


class AmbiguousSongError(LookupError):
    """Raised when multiple songs match the incoming request."""


@dataclass
class SongMatch:
    index: int
    song: Song


class SongCatalog:
    """Provides convenience lookups over the list of songs."""

    def __init__(self, songs: Sequence[Song]):
        self._songs: List[Song] = list(songs)
        self._title_index: Dict[str, int] = {}
        self._number_index: Dict[str, int] = {}
        self._first_by_key: Dict[str, int] = {}

        for index, song in enumerate(self._songs):
            self._title_index[song.normalized_title] = index
            if song.normalized_number:
                self._number_index[song.normalized_number] = index
            key = song.default_jump_key()
            if key and key not in self._first_by_key:
                self._first_by_key[key] = index

    @property
    def songs(self) -> Sequence[Song]:
        return self._songs

    @property
    def first_by_key(self) -> Dict[str, int]:
        return self._first_by_key

    def find(self, *, title: Optional[str] = None, title_number: Optional[str] = None, query: Optional[str] = None) -> SongMatch:
        """Return the song matching the supplied values."""

        attempts: List[str] = []
        if title_number:
            match = self._match_number(title_number)
            if match:
                return match
            attempts.append(title_number)

        for candidate in (title, query):
            if not candidate:
                continue
            match = self._match_title(candidate)
            if match:
                return match
            number, stripped_title = split_title_and_number(candidate)
            if number:
                match = self._match_number(number)
                if match:
                    return match
            if stripped_title and stripped_title != candidate:
                match = self._match_title(stripped_title)
                if match:
                    return match
            attempts.append(candidate)

        fallback = self._fuzzy_match(attempts)
        if fallback:
            return fallback

        raise SongNotFoundError("; ".join(attempts) or "<empty query>")

    def _match_number(self, number: str) -> Optional[SongMatch]:
        normalized = normalize_number(number)
        if not normalized:
            return None
        index = self._number_index.get(normalized)
        if index is None:
            return None
        return SongMatch(index=index, song=self._songs[index])

    def _match_title(self, title: str) -> Optional[SongMatch]:
        normalized = normalize_text(title)
        if not normalized:
            return None
        index = self._title_index.get(normalized)
        if index is None:
            return None
        return SongMatch(index=index, song=self._songs[index])

    def _fuzzy_match(self, attempts: Iterable[str]) -> Optional[SongMatch]:
        candidates: Dict[int, Tuple[int, Song]] = {}
        normalized_attempts = [normalize_text(value) for value in attempts if value]
        for index, song in enumerate(self._songs):
            best_rank: Optional[int] = None
            for attempt in normalized_attempts:
                if not attempt:
                    continue
                if song.normalized_title.startswith(attempt):
                    rank = 0
                elif attempt in song.normalized_title:
                    rank = 1
                else:
                    continue
                if best_rank is None or rank < best_rank:
                    best_rank = rank
            if best_rank is not None:
                current = candidates.get(index)
                if current is None or best_rank < current[0]:
                    candidates[index] = (best_rank, song)

        if not candidates:
            return None

        best_rank = min(value[0] for value in candidates.values())
        best_matches = [SongMatch(index=index, song=song) for index, (rank, song) in candidates.items() if rank == best_rank]

        if len(best_matches) > 1:
            labels = ", ".join(match.song.display_label() for match in best_matches)
            raise AmbiguousSongError(labels)

        return best_matches[0]


__all__ = ["SongCatalog", "SongMatch", "SongNotFoundError", "AmbiguousSongError"]
