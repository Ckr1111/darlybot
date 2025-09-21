from pathlib import Path

import pytest

from darlybot.navigator import NavigationPlan, SongNavigator


@pytest.fixture()
def navigator() -> SongNavigator:
    return SongNavigator(Path(__file__).parent / "data" / "test_songs.csv")


def test_loads_songs(navigator: SongNavigator) -> None:
    assert navigator.song_count == 7
    assert navigator.song_titles[0] == "Airwave"


def test_available_letters(navigator: SongNavigator) -> None:
    assert navigator.available_letters == ["a", "b", "c", "d", "e"]


def test_navigation_plan_first_of_letter(navigator: SongNavigator) -> None:
    plan = navigator.plan_for_title("Dreamer")
    assert plan.letter == "d"
    assert plan.offset == 0
    assert plan.keystrokes() == ["d"]


def test_navigation_plan_second_of_letter(navigator: SongNavigator) -> None:
    plan = navigator.plan_for_title("Binary Star")
    assert plan.letter == "b"
    assert plan.offset == 1
    assert plan.keystrokes() == ["b", "down"]


def test_lookup_is_case_insensitive(navigator: SongNavigator) -> None:
    plan = navigator.plan_for_title("binary sunset")
    assert isinstance(plan, NavigationPlan)


def test_missing_song_raises(navigator: SongNavigator) -> None:
    with pytest.raises(KeyError):
        navigator.plan_for_title("Nonexistent Song")
