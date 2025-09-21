"""Translate song matches into key press plans."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping, Optional

from .catalog import SongCatalog, SongMatch
from .models import SearchPlan

_LOGGER = logging.getLogger(__name__)


@dataclass
class PlanResult:
    plan: SearchPlan
    match: SongMatch


class SearchPlanner:
    """Compute the key presses necessary to navigate to a song."""

    def __init__(self, catalog: SongCatalog):
        self._catalog = catalog

    @property
    def catalog(self) -> SongCatalog:
        return self._catalog

    def plan_from_payload(self, payload: Mapping[str, object]) -> PlanResult:
        title = _extract_first(payload, ["title", "songTitle", "name"])
        title_number = _extract_first(payload, ["titleNumber", "songNumber", "number", "id"])
        query = _extract_first(payload, ["query", "text", "label"])

        match = self.catalog.find(title=title, title_number=title_number, query=query)
        plan = self._build_plan(match)
        return PlanResult(plan=plan, match=match)

    def plan_from_query(self, query: str) -> PlanResult:
        match = self.catalog.find(query=query)
        plan = self._build_plan(match)
        return PlanResult(plan=plan, match=match)

    def _build_plan(self, match: SongMatch) -> SearchPlan:
        preferred_key = match.song.default_jump_key()
        best_plan: Optional[SearchPlan] = None
        best_score: Optional[tuple[int, int, str]] = None

        if not self.catalog.first_by_key:
            _LOGGER.debug("No jump keys available; returning no-op plan")
            return SearchPlan(song=match.song, base_key=None, offset=0)

        for key, base_index in self.catalog.first_by_key.items():
            offset = match.index - base_index
            candidate = SearchPlan(song=match.song, base_key=key, offset=offset)
            score = (abs(offset), 0 if key == preferred_key else 1, key)
            if best_plan is None or score < best_score:
                best_plan = candidate
                best_score = score

        # Fall back to the preferred key even if it was not a first occurrence.
        if best_plan is None and preferred_key:
            base_index = next((i for i, song in enumerate(self.catalog.songs) if song.default_jump_key() == preferred_key), None)
            if base_index is not None:
                offset = match.index - base_index
                best_plan = SearchPlan(song=match.song, base_key=preferred_key, offset=offset)

        if best_plan is None:
            best_plan = SearchPlan(song=match.song, base_key=None, offset=0)

        return best_plan


def _coerce_str(value: object) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _extract_first(mapping: Mapping[str, object], keys: list[str]) -> Optional[str]:
    for key in keys:
        if key in mapping:
            value = _coerce_str(mapping.get(key))
            if value:
                return value
    return None


__all__ = ["SearchPlanner", "PlanResult"]
