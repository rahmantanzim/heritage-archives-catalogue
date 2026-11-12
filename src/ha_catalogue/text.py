"""Text helpers shared by loading and searching."""

from __future__ import annotations

import unicodedata


def search_key(text: str) -> str:
    """Make text comparable for search.

    The same Bengali letter can be stored in two ways: ড় as one character,
    or as ড plus a dot (়). Unicode normalization (NFC) makes them equal.
    Lower-casing makes English search case-insensitive.
    """
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())
