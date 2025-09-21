from pathlib import Path

import pytest

from rofebot_bridge.loader import SongLoadError, load_songs
from tests.utils import data_path


def test_load_songs_with_header() -> None:
    songs = load_songs(data_path("song_order.csv"))
    assert songs[0].title == "Another Day"
    assert songs[0].default_jump_key() == "a"
    assert songs[1].title_number == "002"
    assert songs[1].default_jump_key() == "b"


def test_load_songs_without_header(tmp_path: Path) -> None:
    csv_path = tmp_path / "songs.csv"
    csv_path.write_text("001,Alpha Song\n002,Beta Song\n\n003,Gamma\n", encoding="utf-8")
    songs = load_songs(csv_path)
    assert [song.title for song in songs] == ["Alpha Song", "Beta Song", "Gamma"]


def test_load_songs_invalid_path(tmp_path: Path) -> None:
    with pytest.raises(SongLoadError):
        load_songs(tmp_path / "missing.csv")
