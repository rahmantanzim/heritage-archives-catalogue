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

from ha_catalogue.english import reads_as_english

# --- Detection -------------------------------------------------------------

# SutonnyMJ draws Bengali vowel signs and conjuncts with symbols such as
# ‡ † ¨ © ¯ Ö Ë. Real English catalogue text almost never contains them.
# So: any character outside plain ASCII that isn't Bengali and isn't normal
# typographic punctuation counts as a Bijoy mark. Plus a few ASCII ones.
_ASCII_BIJOY_MARKS = frozenset("^`~")
_TYPOGRAPHIC = frozenset("’‘“”–—…\xa0")

# In Bijoy, "|" is the Bengali full stop (দাঁড়ি).
_DARI = "|"

# Bijoy words often have a capital letter right after a lowercase one
# ("AvRKvj", "evsjv"). English words rarely do.
_MIXED_CASE = re.compile(r"[a-z][A-Z]")
_WORD = re.compile(r"[A-Za-z]{3,}")

_BENGALI_BLOCK = re.compile(r"[ঀ-৿]")


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
    ("šÍ", "š—"),  # ন্ত (library gives ন্ত্ম)
    ("ÿ", "¶"),  # ক্ষ (library leaves ÿ unconverted)
    ("Ð", "Û"),  # ণ্ড/ন্ড (library gives "-")
    ("æ", "z"),  # ু after র, as in নুরুল (library gives ম্ন)
)

_PADDING = "  "
_REPH_BIJOY = "©"
_REPH_MARKER = ""  # a private-use character the library ignores
_REPH = "র্"

_CONSONANT = "[ক-হড়-য়]"
_VOWEL_SIGNS = "[়-ৌৗ]"
# A consonant cluster (e.g. ক, ক্ষ, ন্ত্র), its vowel signs, then the marker.
_REPH_PLACEMENT = re.compile(f"({_CONSONANT}(?:্{_CONSONANT})*)({_VOWEL_SIGNS}*){_REPH_MARKER}")


class ConversionError(ValueError):
    """Raised when Bijoy text cannot be converted."""


@lru_cache(maxsize=1)
def _library_converter():
    from bijoy2unicode import converter

    return converter.Unicode()


def to_unicode(text: str) -> str:
    """Convert Bijoy text to Unicode Bengali."""
    for wrong, right in _PRE_FIXES:
        text = text.replace(wrong, right)
    text = text.replace(_REPH_BIJOY, _REPH_MARKER)
    trailing_space = text[len(text.rstrip()) :]

    try:
        # The library reads past the end of short strings and crashes
        # (e.g. on "GKz‡k"). Two spaces of padding prevent it; we strip them.
        result = _library_converter().convertBijoyToUnicode(text.rstrip() + _PADDING)
    except Exception as exc:  # the library raises bare IndexErrors
        raise ConversionError(f"could not convert {text!r}") from exc
    result = result.rstrip() + trailing_space

    result = _REPH_PLACEMENT.sub(lambda m: _REPH + m.group(1) + m.group(2), result)
    if _REPH_MARKER in result:
        raise ConversionError(f"reph with no consonant before it in {text!r}")
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
            converted.append(to_unicode(part))
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
