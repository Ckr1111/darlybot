from __future__ import annotations

import io
import logging
import sys
from pathlib import Path

import pytest

from darlybot.__main__ import configure_logging


@pytest.fixture(autouse=True)
def cleanup_logging() -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    yield
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    root.setLevel(logging.WARNING)


def test_configure_logging_log_file(tmp_path: Path) -> None:
    log_path = tmp_path / "custom.log"
    configure_logging("DEBUG", log_path)
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert isinstance(handler, logging.FileHandler)
    assert Path(handler.baseFilename) == log_path


def test_configure_logging_fallback_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "stderr", None)
    configure_logging("INFO", None)
    root = logging.getLogger()
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert isinstance(handler, logging.FileHandler)
    assert Path(handler.baseFilename) == tmp_path / "darlybot.log"


def test_configure_logging_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = io.StringIO()
    monkeypatch.setattr(sys, "stderr", stream)
    configure_logging("WARNING", None)
    root = logging.getLogger()
    assert root.level == logging.WARNING
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    assert handler.stream is stream
