"""Utilities for dealing with song titles and identifiers."""

from __future__ import annotations

import re
import unicodedata
from typing import Optional, Tuple

_whitespace_re = re.compile(r"\s+")
_digits_re = re.compile(r"\d+")


def normalize_text(value: Optional[str]) -> str:
    """Return a case-folded, whitespace-normalised version of *value*.

    The function is designed to work well with data coming from CSV files where
    the casing might be inconsistent and extra whitespace may appear.
    """

    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.strip()
    text = _whitespace_re.sub(" ", text)
    return text.casefold()


def normalize_number(value: Optional[str]) -> Optional[str]:
    """Extract a canonical numeric identifier from *value* if possible."""

    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits:
        return None
    stripped = digits.lstrip("0")
    return stripped or "0"


def extract_initial_key(title: str, *, preferred: Optional[str] = None) -> Optional[str]:
    """Return the first character that can be used as a jump hotkey.

    Letters take precedence, but when no latin letter is present digits are
    returned.  ``preferred`` can be used to override the detected value when a
    CSV file explicitly provides the key to use.
    """

    if preferred:
        return preferred.lower()

    normalized = normalize_text(title)
    for char in normalized:
        if "a" <= char <= "z":
            return char
        if char.isdigit():
            return char
    return None


def split_title_and_number(text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Split *text* into a ``(title_number, title)`` tuple when possible."""

    if text is None:
        return None, None

    raw = unicodedata.normalize("NFKC", str(text)).strip()
    if not raw:
        return None, None

    match = re.match(r"^(?P<num>\d+)[\s\-:./]*?(?P<title>.*)$", raw)
    if match:
        number = normalize_number(match.group("num"))
        title = match.group("title").strip() or None
        return number, title

    numbers = _digits_re.findall(raw)
    if len(numbers) == 1:
        number = normalize_number(numbers[0])
    else:
        number = None
    return number, raw


__all__ = [
    "normalize_text",
    "normalize_number",
    "extract_initial_key",
    "split_title_and_number",
]
