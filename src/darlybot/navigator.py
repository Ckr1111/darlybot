"""High level orchestration for selecting songs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from .song_index import SongEntry, SongIndex, SongNotFoundError

__all__ = ["NavigationError", "NavigationResult", "SongNavigator"]


class NavigationError(RuntimeError):
    """Raised when the navigator cannot perform the requested action."""


@dataclass
class NavigationResult:
    """Information about a navigation request.

    Attributes
    ----------
    entry:
        The matched :class:`~darlybot.song_index.SongEntry` instance.
    keys:
        The exact sequence of key strings that were generated.
    performed:
        Whether the input controller actually sent the key presses.  This will
        be ``False`` when running in ``dry_run`` mode.
    """

    entry: SongEntry
    keys: Sequence[str]
    performed: bool


class SongNavigator:
    """Orchestrates locating the desired song and sending the key sequence."""

    def __init__(self, index: SongIndex, controller: "InputController"):
        self.index = index
        self.controller = controller

    def navigate(
        self,
        *,
        title_number: Optional[str] = None,
        title: Optional[str] = None,
        dry_run: bool = False,
    ) -> NavigationResult:
        """Navigate to the requested song.

        Parameters
        ----------
        title_number:
            The ``title_number`` column from ``default.csv``.
        title:
            The human readable title.  Case is ignored.
        dry_run:
            When ``True`` the method only returns the generated key sequence and
            does not send any key events.
        """

        if not title_number and not title:
            raise NavigationError("title 또는 title_number 중 하나는 반드시 필요합니다.")

        entry = self._resolve_entry(title_number=title_number, title=title)
        keys = self.index.key_sequence_for(entry)
        performed = False

        if not dry_run:
            try:
                self.controller.focus_window()
                self.controller.send_keys(keys)
            except Exception as exc:  # pragma: no cover - integration layer
                raise NavigationError(str(exc)) from exc
            performed = True

        return NavigationResult(entry=entry, keys=tuple(keys), performed=performed)

    def _resolve_entry(
        self, *, title_number: Optional[str], title: Optional[str]
    ) -> SongEntry:
        if title_number:
            try:
                return self.index.get_by_title_number(title_number)
            except SongNotFoundError:
                # If the caller provided both fields we still want to try the
                # title before raising an error, so we only re-raise when there
                # is nothing else to try.
                if not title:
                    raise
        if title:
            return self.index.get_by_title(title)
        raise SongNotFoundError("요청하신 곡을 찾을 수 없습니다.")


class InputController:  # pragma: no cover - interface definition
    """Minimal protocol implemented by :mod:`darlybot.input_controller`."""

    def focus_window(self) -> None:
        raise NotImplementedError

    def send_keys(self, keys: Iterable[str]) -> None:
        raise NotImplementedError
