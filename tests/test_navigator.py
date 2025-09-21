import pytest

from darlybot.input_controller import SimulatedInputController
from darlybot.navigator import NavigationError, SongNavigator
from darlybot.song_index import SCROLL_DOWN_KEY, SongIndex


@pytest.fixture()
def sample_index(tmp_path):
    src = tmp_path / "곡순서.csv"
    src.write_text(
        "title_number,title\n0001,Alpha\n0002,Beta\n0003,Bolt\n0004,Charlie\n",
        encoding="utf-8",
    )
    return SongIndex(src)


def test_dry_run_does_not_trigger_controller(sample_index):
    controller = SimulatedInputController()
    navigator = SongNavigator(sample_index, controller)
    result = navigator.navigate(title="Bolt", dry_run=True)
    assert result.keys == ("b", SCROLL_DOWN_KEY)
    assert not controller.sent_keys
    assert not result.performed


def test_navigate_sends_keys(sample_index):
    controller = SimulatedInputController()
    navigator = SongNavigator(sample_index, controller)
    result = navigator.navigate(title_number="0003")
    assert controller.focused
    assert controller.sent_keys == ["b", SCROLL_DOWN_KEY]
    assert result.performed


def test_missing_arguments_raise(sample_index):
    controller = SimulatedInputController()
    navigator = SongNavigator(sample_index, controller)
    with pytest.raises(NavigationError):
        navigator.navigate()
