"""Detect legacy Bijoy (SutonnyMJ) text and convert it to Unicode Bengali.

Many older Heritage Archives catalogue entries were typed with the Bijoy
keyboard in a SutonnyMJ font. The file stores ordinary Latin characters and
the font draws them as Bengali. Outside that font the text looks like
"Kv‡e`yj Bmjvg" instead of "কাবেদুল ইসলাম", and it cannot be searched.

How conversion works:
1. `is_bijoy` decides whether a piece of text is Bijoy. Real English and
   Unicode Bengali are left alone.
2. A few characters the converter library maps wrongly are replaced first
   (`_PRE_FIXES`).
3. The reph sign (র্, typed as "©") is taken out and replaced by a marker,
   because the library places it wrongly and can crash on it.
4. The `bijoy2unicode` library converts the rest.
5. We put each reph back in front of the consonant it belongs to.

Every rule here was found by checking converted catalogue lines by hand.
The tests in tests/test_encoding.py hold those real examples.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from functools import lru_cache

from bijoy2unicode import converter

from ha_catalogue.english import reads_as_english

# --- Detection -------------------------------------------------------------

# SutonnyMJ draws Bengali vowel signs and conjuncts with symbols such as
# ‡ † ¨ © ¯ Ö Ë. Real English catalogue text almost never contains them.
# So: any character outside plain ASCII that isn't Bengali and isn't normal
# typographic punctuation counts as a Bijoy mark. Plus a few ASCII ones.
_ASCII_BIJOY_MARKS = frozenset("^`~")
_TYPOGRAPHIC = frozenset("\u2019\u2018\u201c\u201d\u2013\u2014\u2026\xa0")  # ’ ‘ “ ” – — … nbsp

# In Bijoy, "|" is the Bengali full stop (দাঁড়ি).
_DARI = "|"

# Bijoy words often have a capital letter right after a lowercase one
# ("AvRKvj", "evsjv"). English words rarely do.
_MIXED_CASE = re.compile(r"[a-z][A-Z]")
_WORD = re.compile(r"[A-Za-z]{3,}")

_BENGALI_BLOCK = re.compile("[\u0980-\u09ff]")


def _is_bijoy_mark(ch: str) -> bool:
    if ch in _ASCII_BIJOY_MARKS:
        return True
    return not ch.isascii() and ch not in _TYPOGRAPHIC


def is_bijoy(text: str) -> bool:
    """Return True if `text` looks like Bijoy-encoded Bengali."""
    if not text or not text.strip():
        return False
    if _BENGALI_BLOCK.search(text):  # already Unicode Bengali
        return False
    if any(_is_bijoy_mark(ch) for ch in text):
        return True
    words = _WORD.findall(text)
    if not words:
        return False
    if text.rstrip().endswith(_DARI):
        return True
    mixed = sum(1 for word in words if _MIXED_CASE.search(word))
    return mixed / len(words) >= 0.5


# --- Conversion ------------------------------------------------------------

# Characters the library maps wrongly, replaced with the Bijoy form it
# handles correctly. Found by checking real catalogue lines.
_PRE_FIXES: tuple[tuple[str, str], ...] = (
    ("Í", "—"),  # ত as in ন্ত, স্ত (library gives ত্ম: পাকিস্ত্মান)
    ("ÿ", "¶"),  # ক্ষ (library leaves ÿ unconverted)
    ("Ð", "Û"),  # ণ্ড/ন্ড (library gives "-")
    ("æ", "z"),  # ু after র, as in নুরুল (library gives ম্ন)
)

_PADDING = "  "
# Signs the library places wrongly. Each is swapped for a private-use marker
# (a character the library passes through untouched), the library converts
# the rest, and we attach the sign to the right consonant cluster ourselves.
_REPH_BIJOY = "©"  # র্ on top: goes BEFORE its cluster (নির্বাচন)
_LA_FALA_BIJOY = "ø"  # ্ল below: goes AFTER its cluster (পল্লী, ব্লি); library gives স্ন
_RA_YA_FALA_BIJOY = "ª¨"  # ্র then ্য (ব্র্যাক); library gives বর্য
_REPH_MARKER = "\ue000"
_LA_FALA_MARKER = "\ue001"
_YA_FALA_MARKER = "\ue002"
_MARKERS = (_REPH_MARKER, _LA_FALA_MARKER, _YA_FALA_MARKER)
_REPH = "\u09b0\u09cd"  # র্
_LA_FALA = "\u09cd\u09b2"  # ্ল
_YA_FALA = "\u09cd\u09af"  # ্য

_CONSONANT = "[\u0995-\u09b9\u09dc-\u09df]"  # ক-হ, ড়-য়
_VOWEL_SIGNS = "[\u09bc-\u09cc\u09d7]"  # nukta, া-ৌ, ৗ
# A consonant cluster (e.g. ক, ক্ষ, ন্ত্র) and its vowel signs, before a marker.
_CLUSTER = f"({_CONSONANT}(?:\u09cd{_CONSONANT})*)({_VOWEL_SIGNS}*)"
_REPH_PLACEMENT = re.compile(_CLUSTER + _REPH_MARKER)
_LA_FALA_PLACEMENT = re.compile(_CLUSTER + _LA_FALA_MARKER)
_YA_FALA_PLACEMENT = re.compile(_CLUSTER + _YA_FALA_MARKER)


class ConversionError(ValueError):
    """Raised when Bijoy text cannot be converted."""


@lru_cache(maxsize=1)
def _library_converter() -> converter.Unicode:
    return converter.Unicode()


def to_unicode(text: str) -> str:
    """Convert Bijoy text to Unicode Bengali."""
    for wrong, right in _PRE_FIXES:
        text = text.replace(wrong, right)
    text = (
        text.replace(_RA_YA_FALA_BIJOY, "ª" + _YA_FALA_MARKER)
        .replace(_LA_FALA_BIJOY, _LA_FALA_MARKER)
        .replace(_REPH_BIJOY, _REPH_MARKER)
    )
    trailing_space = text[len(text.rstrip()) :]

    try:
        # The library reads past the end of short strings and crashes
        # (e.g. on "GKz‡k"). Two spaces of padding prevent it; we strip them.
        result = _library_converter().convertBijoyToUnicode(text.rstrip() + _PADDING)
    except Exception as exc:  # the library raises bare IndexErrors
        raise ConversionError(f"could not convert {text!r}") from exc
    result = result.rstrip() + trailing_space

    # Signs below a letter join its cluster first; then the reph goes before
    # the whole cluster.
    result = _LA_FALA_PLACEMENT.sub(lambda m: m.group(1) + _LA_FALA + m.group(2), result)
    result = _YA_FALA_PLACEMENT.sub(lambda m: m.group(1) + _YA_FALA + m.group(2), result)
    result = _REPH_PLACEMENT.sub(lambda m: _REPH + m.group(1) + m.group(2), result)
    if any(marker in result for marker in _MARKERS):
        raise ConversionError(f"a sign with no consonant before it in {text!r}")
    return result


# --- Public entry point ----------------------------------------------------


@dataclass(frozen=True)
class NormalizedText:
    """Result of cleaning one piece of catalogue text."""

    text: str
    original: str
    converted: bool
    error: str | None = None


# A cell can mix English and Bijoy, e.g.
# "Anual Report 2010-11, kgwPZv nvmcvZvj wj:, XvKv|".
# We split it at these separators and convert only the Bijoy sections.
# A cross-reference ("see 400.13 (93)") also starts a new section.
_SECTION_SEPARATOR = re.compile(r"([,;:]\s*|\s+(?=(?:also\s+)?see\b))")
# A leading label like "(R) " or "(S) " is a code, not Bengali text.
_LABEL_PREFIX = re.compile(r"^\([A-Z]\)\s*")
# Cross-references are written in English and must be kept as they are.
_CROSS_REFERENCE = re.compile(r"^\(?(?:also\s+)?see\b", re.IGNORECASE)
# An English acronym inside a Bijoy section ("TMSS evZ©v", "RDRS."). Bijoy
# also writes Bengali in capitals ("GK" = এক, "FY" = ঋণ, "GBW" = এইড), but in
# this catalogue only 4+ capital letters are always English.
_ACRONYM = re.compile(r"^\(?[A-Z]{4,}\)?[.,:;)]*$")
_WHITESPACE = re.compile(r"(\s+)")
# Short Bijoy words like "Ryb" (জুন) can pass the English test, so a
# section needs at least this many letters to be kept as English.
_MIN_ENGLISH_SECTION_LETTERS = 4


def _keep_as_english(section: str) -> bool:
    if _CROSS_REFERENCE.match(section.strip()):
        return True
    if is_bijoy(section):
        return False
    letters = sum(ch.isascii() and ch.isalpha() for ch in section)
    return letters >= _MIN_ENGLISH_SECTION_LETTERS and reads_as_english(section)


def _convert_bijoy_section(section: str) -> str:
    """Convert a Bijoy section, keeping English acronyms inside it."""
    pieces: list[str] = []
    pending = ""
    for token in _WHITESPACE.split(section):
        if _ACRONYM.match(token):
            pieces.append(to_unicode(pending) if pending.strip() else pending)
            pieces.append(token)
            pending = ""
        else:
            pending += token
    pieces.append(to_unicode(pending) if pending.strip() else pending)
    return "".join(pieces)


def _convert_sections(text: str) -> str:
    label = _LABEL_PREFIX.match(text)
    prefix = label.group(0) if label else ""
    parts = _SECTION_SEPARATOR.split(text[len(prefix) :])
    converted: list[str] = []
    for index, part in enumerate(parts):
        is_separator = index % 2 == 1
        if is_separator or not part.strip() or _keep_as_english(part):
            converted.append(part)
        else:
            converted.append(_convert_bijoy_section(part))
    return prefix + "".join(converted)


def normalize(text: str) -> NormalizedText:
    """Clean one piece of text.

    Unicode Bengali and English pass through (trimmed). Bijoy is converted,
    section by section, so English sections inside the same cell are kept.
    If conversion fails, the original is kept and the error is recorded, so
    one bad line never stops a whole catalogue from loading.
    """
    original = text
    cleaned = " ".join(text.split())
    if not is_bijoy(cleaned):
        return NormalizedText(cleaned, original, converted=False)
    try:
        return NormalizedText(_convert_sections(cleaned), original, converted=True)
    except ConversionError as exc:
        return NormalizedText(cleaned, original, converted=False, error=str(exc))


if __name__ == "__main__":
    # Try it: python -m ha_catalogue.encoding "Kv‡e`yj Bmjvg"
    for arg in sys.argv[1:]:
        result = normalize(arg)
        print(f"{arg}  ->  {result.text}  (converted={result.converted})")
