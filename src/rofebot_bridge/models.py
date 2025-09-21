"""Domain models used by the bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import text_utils


@dataclass(frozen=True)
class Song:
    """Representation of a single entry in ``곡순서.csv``."""

    title: str
    title_number: Optional[str] = None
    jump_key: Optional[str] = None
    normalized_title: str = ""
    normalized_number: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "normalized_title", text_utils.normalize_text(self.title))
        number = text_utils.normalize_number(self.title_number)
        object.__setattr__(self, "normalized_number", number)
        if self.jump_key:
            object.__setattr__(self, "jump_key", self.jump_key.lower())

    def display_label(self) -> str:
        if self.title_number:
            return f"{self.title_number} {self.title}"
        return self.title

    def default_jump_key(self) -> Optional[str]:
        return text_utils.extract_initial_key(self.title, preferred=self.jump_key)

    def matches_title(self, candidate: str) -> bool:
        return text_utils.normalize_text(candidate) == self.normalized_title

    def matches_number(self, candidate: str) -> bool:
        normalized = text_utils.normalize_number(candidate)
        return bool(normalized) and normalized == self.normalized_number


@dataclass(frozen=True)
class SearchPlan:
    """Describes the key presses required to focus a given song."""

    song: Song
    base_key: Optional[str]
    offset: int

    @property
    def direction(self) -> str:
        if self.offset > 0:
            return "down"
        if self.offset < 0:
            return "up"
        return "none"

    @property
    def arrow_count(self) -> int:
        return abs(self.offset)

    def as_key_sequence(self) -> list[str]:
        sequence: list[str] = []
        if self.base_key:
            sequence.append(self.base_key)
        if self.offset > 0:
            sequence.extend(["{DOWN}"] * self.offset)
        elif self.offset < 0:
            sequence.extend(["{UP}"] * (-self.offset))
        return sequence


__all__ = ["Song", "SearchPlan"]
