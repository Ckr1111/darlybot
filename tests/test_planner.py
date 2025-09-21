import pytest

from rofebot_bridge import SearchPlanner, SongCatalog, load_songs
from rofebot_bridge.catalog import AmbiguousSongError

from tests.utils import data_path


def _planner() -> SearchPlanner:
    songs = load_songs(data_path("song_order.csv"))
    return SearchPlanner(SongCatalog(songs))


def test_plan_uses_initial_letter() -> None:
    planner = _planner()
    result = planner.plan_from_query("Binary World")
    assert result.plan.base_key == "b"
    assert result.plan.offset == 0


def test_plan_for_remix_song_uses_arrow_keys() -> None:
    planner = _planner()
    result = planner.plan_from_query("Binary World (Remix)")
    assert result.plan.base_key == "b"
    assert result.plan.offset == 1
    assert result.plan.as_key_sequence() == ["b", "{DOWN}"]


def test_plan_from_number_payload() -> None:
    planner = _planner()
    result = planner.plan_from_payload({"titleNumber": "024"})
    assert result.match.song.title == "Midnight Bloom"
    assert result.plan.base_key == "m"


def test_ambiguous_queries_raise() -> None:
    planner = _planner()
    with pytest.raises(AmbiguousSongError):
        planner.catalog.find(query="Binary")
