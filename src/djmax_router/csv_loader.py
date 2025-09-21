"""CSV loading utilities for DJMAX song metadata."""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Song:
    """Representation of a single song entry."""

    title_number: str
    title: str
    group_key: str
    index_in_group: int
    tile_id: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "titleNumber": self.title_number,
            "title": self.title,
            "groupKey": self.group_key,
            "indexInGroup": self.index_in_group,
            "tileId": self.tile_id,
        }


def _normalise_field_name(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _compute_group_key(title: str) -> str:
    title = title.strip()
    for char in title:
        if char.isalpha():
            return char.lower()
        if char.isdigit():
            return char
    return "#"


class SongLibrary:
    """Loads and exposes song metadata from a CSV file."""

    def __init__(self, csv_path: Path) -> None:
        self.csv_path = csv_path
        self._songs: List[Song] = []
        self._by_title_number: Dict[str, Song] = {}
        self._by_title: Dict[str, Song] = {}
        self._by_tile_id: Dict[str, Song] = {}
        self._groups: Dict[str, List[Song]] = {}
        self.reload()

    @property
    def songs(self) -> Iterable[Song]:
        return tuple(self._songs)

    def find_by_title_number(self, value: str) -> Optional[Song]:
        if value is None:
            return None
        return self._by_title_number.get(value.strip().lower())

    def find_by_title(self, value: str) -> Optional[Song]:
        if value is None:
            return None
        return self._by_title.get(value.strip().lower())

    def find_by_tile_id(self, value: str) -> Optional[Song]:
        if value is None:
            return None
        return self._by_tile_id.get(value.strip().lower())

    def list_group(self, group_key: str) -> List[Song]:
        return list(self._groups.get(group_key.lower(), ()))

    def reload(self) -> None:
        self._songs.clear()
        self._by_title_number.clear()
        self._by_title.clear()
        self._by_tile_id.clear()
        self._groups.clear()

        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        LOGGER.info("Loading song metadata from %s", self.csv_path)
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None:
                raise ValueError("CSV file must include a header row")
            for row in reader:
                normalised = {_normalise_field_name(k): (v or "").strip() for k, v in row.items()}
                title = normalised.get("title") or normalised.get("곡명")
                title_number = (
                    normalised.get("title_number")
                    or normalised.get("titlenumber")
                    or normalised.get("titleid")
                    or normalised.get("title_no")
                    or normalised.get("no")
                    or normalised.get("id")
                )
                tile_id = normalised.get("tile_id") or title_number
                if not title or not title_number:
                    LOGGER.warning("Skipping row missing title or title number: %s", row)
                    continue

                group_key = _compute_group_key(title)
                group = self._groups.setdefault(group_key, [])
                song = Song(
                    title_number=title_number,
                    title=title,
                    group_key=group_key,
                    index_in_group=len(group),
                    tile_id=tile_id or title_number,
                )
                group.append(song)
                self._songs.append(song)
                self._by_title_number[title_number.strip().lower()] = song
                self._by_title[title.strip().lower()] = song
                if tile_id:
                    self._by_tile_id[tile_id.strip().lower()] = song

        LOGGER.info("Loaded %d songs from %s", len(self._songs), self.csv_path)
