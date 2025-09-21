from pathlib import Path

import pytest

from darlybot.song_index import (
    SCROLL_DOWN_KEY,
    SongIndex,
    SongNotFoundError,
)


@pytest.fixture()
def sample_index(tmp_path: Path) -> SongIndex:
    csv_path = tmp_path / "곡순서.csv"
    csv_path.write_text(
        """title_number,title
0001,漢字의 꿈
0002,가을 바람
0003,!Exclaim
0004,123 BPM
0005,Alpha
0006,Beautiful Day
0007,Bullet Strike
""",
        encoding="utf-8",
    )
    return SongIndex(csv_path)


def test_lookup_by_title_number(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0007")
    assert entry.title == "Bullet Strike"
    assert entry.letter == "B"


def test_lookup_by_title_is_case_insensitive(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title("beautiful day")
    assert entry.title_number == "0006"


def test_key_sequence_for_first_letter_entry(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0005")
    sequence = sample_index.key_sequence_for(entry)
    assert sequence == ["shift_r", "shift", "a"]


def test_key_sequence_for_later_entry(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0007")
    sequence = sample_index.key_sequence_for(entry)
    assert sequence == ["shift_r", "shift", "b", SCROLL_DOWN_KEY]


def test_key_sequence_for_hanja_title(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0001")
    assert entry.letter == "한자"
    sequence = sample_index.key_sequence_for(entry)
    assert sequence == ["shift_r", "shift"]


def test_key_sequence_for_hangul_title(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0002")
    assert entry.letter == "한글"
    sequence = sample_index.key_sequence_for(entry)
    assert sequence == ["shift_r", "shift", SCROLL_DOWN_KEY]


def test_key_sequence_for_symbol_title(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0003")
    assert entry.letter == "특수문자"
    sequence = sample_index.key_sequence_for(entry)
    assert sequence == ["shift_r", "shift", SCROLL_DOWN_KEY, SCROLL_DOWN_KEY]


def test_key_sequence_for_number_title(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0004")
    assert entry.letter == "숫자"
    sequence = sample_index.key_sequence_for(entry)
    assert sequence == [
        "shift_r",
        "shift",
        SCROLL_DOWN_KEY,
        SCROLL_DOWN_KEY,
        SCROLL_DOWN_KEY,
    ]


def test_missing_song_raises(sample_index: SongIndex) -> None:
    with pytest.raises(SongNotFoundError):
        sample_index.get_by_title_number("9999")
