from pathlib import Path

from darlybot.default_songs import DEFAULT_SONG_CSV


def test_embedded_csv_matches_sample_files() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    csv_paths = [
        repo_root / "data" / "곡순서.csv",
        repo_root / "src" / "darlybot" / "data" / "곡순서.csv",
    ]

    for path in csv_paths:
        assert path.read_text(encoding="utf-8") == DEFAULT_SONG_CSV
