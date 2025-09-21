from pathlib import Path

import pytest

from darlybot.song_index import SongIndex, SongNotFoundError


@pytest.fixture()
def sample_index(tmp_path: Path) -> SongIndex:
    # Copy the repository sample data into a temporary directory to avoid
    # accidentally mutating the original file.
    src = Path(__file__).resolve().parents[1] / "data" / "곡순서.csv"
    target = tmp_path / "곡순서.csv"
    target.write_bytes(src.read_bytes())
    return SongIndex(target)


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
    assert sequence == ["b", "down"]


def test_key_sequence_for_hangul_title(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0007")
    assert entry.letter == "한글"
    sequence = sample_index.key_sequence_for(entry)
    assert sequence == ["a", "pageup"]


def test_key_sequence_for_symbol_title(sample_index: SongIndex) -> None:
    entry = sample_index.get_by_title_number("0008")
    assert entry.letter == "특수문자"
    sequence = sample_index.key_sequence_for(entry)
    assert sequence == ["a", "pagedown"]


def test_missing_song_raises(sample_index: SongIndex) -> None:
    with pytest.raises(SongNotFoundError):
        sample_index.get_by_title_number("9999")
