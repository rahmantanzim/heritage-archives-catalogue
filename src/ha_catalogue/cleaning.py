"""Clean one catalogue cell: fix encoding problems and tidy whitespace.

This is the single place readers call to clean text. It combines the two
encoding fixes:

- Bijoy text -> Unicode Bengali (see `encoding.py`)
- English wrongly turned into Bengali letters -> English (see
  `garbled_english.py`)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ha_catalogue.encoding import normalize
from ha_catalogue.garbled_english import recover_english

# Cells that mean "nothing here". নাই = "none" (common in the leaflet dates).
_EMPTY_MARKERS = frozenset({"", "-", "--", "\u2014", "\u09a8\u09be\u0987"})


class Fix(StrEnum):
    """What, if anything, was changed in a cell."""

    NONE = "none"
    BIJOY_CONVERTED = "bijoy_converted"
    ENGLISH_RECOVERED = "english_recovered"


@dataclass(frozen=True)
class CleanCell:
    text: str | None  # None means the cell was empty
    original: str
    fix: Fix = Fix.NONE
    error: str | None = None


def clean_cell(raw: str) -> CleanCell:
    """Clean one cell. Never raises: problems are returned in `error`."""
    collapsed = " ".join(raw.replace("\xa0", " ").split())
    if collapsed in _EMPTY_MARKERS:
        return CleanCell(text=None, original=raw)

    english = recover_english(collapsed)
    if english is not None:
        return CleanCell(text=english, original=raw, fix=Fix.ENGLISH_RECOVERED)

    result = normalize(collapsed)
    fix = Fix.BIJOY_CONVERTED if result.converted else Fix.NONE
    return CleanCell(text=result.text, original=raw, fix=fix, error=result.error)
