from pathlib import Path


def data_path(filename: str) -> Path:
    return Path(__file__).parent / "data" / filename
