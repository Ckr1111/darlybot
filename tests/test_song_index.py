from pathlib import Path

import pytest

from darlybot.song_index import (
    SCROLL_DOWN_KEY,
    SCROLL_UP_KEY,
    SongIndex,
    SongNotFoundError,
)


@pytest.fixture()
def sample_index(tmp_path: Path) -> SongIndex:
    csv_path = tmp_path / "곡순서.csv"
    csv_path.write_text(
        """title_number,title
0008,!Exclaim
0007,가을 바람
0001,Alpha
0002,Beautiful Day
0003,Bullet Strike
""",
        encoding="utf-8",
    )
    return SongIndex(csv_path)


def test_lookup_by_title_number(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0003")
    assert entry.title == "Bullet Strike"
    assert entry.letter == "B"


def test_lookup_by_title_is_case_insensitive(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title("beautiful day")
    assert entry.title_number == "0002"


def test_key_sequence_for_first_letter_entry(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0002")
    sequence = sample_index.key_sequence_for(entry)
    assert sequence == ["b"]


def test_key_sequence_for_later_entry(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0003")
    sequence = sample_index.key_sequence_for(entry)
    assert sequence == ["b", SCROLL_DOWN_KEY]


def test_key_sequence_for_hangul_title(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0007")
    assert entry.letter == "한글"
    sequence = sample_index.key_sequence_for(entry)
    assert sequence == ["a", SCROLL_UP_KEY]


def test_key_sequence_for_symbol_title(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0008")
    assert entry.letter == "특수문자"
    sequence = sample_index.key_sequence_for(entry)
    assert sequence == ["a", "pagedown"]


def test_missing_song_raises(sample_index: SongIndex) -> None:
    with pytest.raises(SongNotFoundError):
        sample_index.get_by_title_number("9999")
