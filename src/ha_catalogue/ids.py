"""Parse the many ID formats in the catalogue into one standard form.

Every item gets a catalogue number and an item number, written as
"catalogue/number", e.g. "189.13/527" or "256/12".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# "189.13 (527)", "189.1.(29A)", "189.9a (146)", "189.22 (96)  e"
_CATALOGUE_AND_NUMBER = re.compile(
    r"^(?P<catalogue>\d+(?:\.\d+[a-zA-Z]?)*)\.?\s*"
    r"\(\s*(?P<number>\d+[a-zA-Z]?)\s*\)"
    r"(?P<rest>.*)$"
)

# A poster number: "12"
_PLAIN_NUMBER = re.compile(r"^\d+$")

# A reserved range: "3476-3500 ফাঁকা" (ফাঁকা = blank). In the source it is
# still in Bijoy ("duvKv"), so we accept both spellings.
_RESERVED_RANGE = re.compile(r"^(?P<start>\d+)\s*-\s*(?P<end>\d+)\s*(?:ফাঁকা|duvKv)$")

# Catalogue numbers mentioned in free text, e.g. "155/155a", "400.25",
# "36NAZ", "F224A". Not part of a longer number.
_CATALOGUE_REFERENCE = re.compile(r"(?<![\d.])\d{1,3}(?:\.\d+)*(?:[A-Za-z]{1,3})?(?![\d])")


@dataclass(frozen=True)
class ParsedId:
    catalogue: str
    number: str
    leftover: str = ""  # unexpected text after the ID, kept for review


def _clean(raw: str) -> str:
    return " ".join(raw.replace("\xa0", " ").split())


def parse_catalogue_id(raw: str) -> ParsedId | None:
    """Parse "189.13 (527)"-style IDs. Returns None if it doesn't match."""
    match = _CATALOGUE_AND_NUMBER.match(_clean(raw))
    if not match:
        return None
    return ParsedId(
        catalogue=match["catalogue"].lower(),
        number=match["number"].lower(),
        leftover=match["rest"].strip(),
    )


def parse_plain_number(raw: str) -> str | None:
    """Parse a bare item number such as a poster number."""
    cleaned = _clean(raw)
    return cleaned if _PLAIN_NUMBER.match(cleaned) else None


def parse_reserved_range(text: str) -> tuple[int, int] | None:
    """Parse "3476-3500 duvKv", a block of numbers kept blank on purpose."""
    match = _RESERVED_RANGE.match(_clean(text))
    if not match:
        return None
    return int(match["start"]), int(match["end"])


def find_catalogue_references(text: str) -> tuple[str, ...]:
    """Return the catalogue numbers mentioned in text, in order, no repeats."""
    seen: dict[str, None] = {}
    for match in _CATALOGUE_REFERENCE.finditer(text):
        seen.setdefault(match.group(0).lower(), None)
    return tuple(seen)
