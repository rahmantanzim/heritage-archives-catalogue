"""Parse the many ID formats in the catalogue into one standard form.

Every item gets a catalogue number and an item number, written as
"catalogue/number", e.g. "189.13/527", "256/12" or "36rab/1".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# The catalogue part: "1", "1a", "30.2.1", "189.9a", "36 RAB", "36 PC",
# and typos with a space after a dot ("30.2. 1").
_CATALOGUE = r"\d+(?:\.\s?\d+[a-zA-Z]?)*[a-zA-Z]?(?:\s?[A-Za-z]{2,3})?"

# "189.13 (527)", "189.1.(29A)", "36 RAB (1)", "1a (1.2)", "222a (21-2-1927)",
# "91c (দ্বাদশ খণ্ড)" (a volume name), "189.22 (96)  e" (leftover "e" is kept
# for review)
MAX_NUMBER_LENGTH = 40
_CATALOGUE_AND_NUMBER = re.compile(
    rf"^(?P<catalogue>{_CATALOGUE})\.?\s*"
    rf"\(\s*(?P<number>[^()\s][^()]{{0,{MAX_NUMBER_LENGTH - 1}}}?)\s*\)"
    r"(?P<rest>.*)$"
)

# A section heading in a category catalogue: an ID with no item number,
# e.g. "131" or "78.1".
_HEADING_ID = re.compile(rf"^{_CATALOGUE}\.?$")

# A lettered series: "CD-01" (CDs listed under press releases)
_SERIES_ID = re.compile(r"^(?P<series>[A-Za-z]{1,4})\s*-\s*(?P<number>\d+)$")

# A number in a numbered list: "12", "4656K"
_PLAIN_NUMBER = re.compile(r"^\d+[A-Za-z]?$")

# A block of numbers kept blank on purpose: "1901-2000", or "3476-3500 ফাঁকা"
# (ফাঁকা = blank; still in Bijoy as "duvKv" in the poster file).
_RESERVED_RANGE = re.compile(r"^(?P<start>\d+)\s*-\s*(?P<end>\d+)\s*(?:ফাঁকা|duvKv)?$")

# Catalogue numbers mentioned in free text, e.g. "155/155a", "400.25",
# "36NAZ", "F224A". Not part of a longer number.
_CATALOGUE_REFERENCE = re.compile(r"(?<![\d.])\d{1,3}(?:\.\d+)*(?:[A-Za-z]{1,3})?(?![\d])")


@dataclass(frozen=True)
class ParsedId:
    catalogue: str
    number: str
    leftover: str = ""  # unexpected text after the ID, kept for review


def clean_id(raw: str) -> str:
    """Collapse non-breaking spaces and runs of whitespace."""
    return " ".join(raw.replace("\xa0", " ").split())


def normalize_catalogue(catalogue: str) -> str:
    """ "36 RAB" -> "36rab", "30.2. 1" -> "30.2.1", "189.9A" -> "189.9a"."""
    return re.sub(r"\s+", "", catalogue).lower()


def parse_catalogue_id(raw: str) -> ParsedId | None:
    """Parse "catalogue (number)" IDs. Returns None if it doesn't match."""
    match = _CATALOGUE_AND_NUMBER.match(clean_id(raw))
    if not match:
        return None
    return ParsedId(
        catalogue=normalize_catalogue(match["catalogue"]),
        number=clean_id(match["number"]).lower(),
        leftover=match["rest"].strip(),
    )


def parse_series_id(raw: str) -> ParsedId | None:
    """Parse "CD-01" as catalogue "cd", number "01"."""
    match = _SERIES_ID.match(clean_id(raw))
    if not match:
        return None
    return ParsedId(catalogue=match["series"].lower(), number=match["number"])


def is_heading_id(raw: str) -> bool:
    """True for an ID with no item number, like "131" or "78.1"."""
    return bool(_HEADING_ID.match(clean_id(raw)))


def parse_plain_number(raw: str) -> str | None:
    """Parse a number in a numbered list, such as a poster number."""
    cleaned = clean_id(raw)
    return cleaned.lower() if _PLAIN_NUMBER.match(cleaned) else None


def parse_reserved_range(text: str) -> tuple[int, int] | None:
    """Parse "1901-2000" or "3476-3500 duvKv", numbers kept blank on purpose."""
    match = _RESERVED_RANGE.match(clean_id(text))
    if not match:
        return None
    return int(match["start"]), int(match["end"])


def find_catalogue_references(text: str) -> tuple[str, ...]:
    """Return the catalogue numbers mentioned in text, in order, no repeats."""
    seen: dict[str, None] = {}
    for match in _CATALOGUE_REFERENCE.finditer(text):
        seen.setdefault(match.group(0).lower(), None)
    return tuple(seen)
