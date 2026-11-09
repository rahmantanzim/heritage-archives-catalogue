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

# --- Detection -------------------------------------------------------------

# Characters SutonnyMJ uses for Bengali vowel signs and conjuncts.
# Real English catalogue text almost never contains them.
_BIJOY_MARKS = frozenset("‡†¨©¯¿Ö¦ˆ‰Š¤§¶µ¾½¼÷×Õ›¡¢£¥«»®°±´·¸¹º¬^`~ÔÿÐæšÍÛ")

# In Bijoy, "|" is the Bengali full stop (দাঁড়ি).
_DARI = "|"

# Bijoy words often have a capital letter right after a lowercase one
# ("AvRKvj", "evsjv"). English words rarely do.
_MIXED_CASE = re.compile(r"[a-z][A-Z]")
_WORD = re.compile(r"[A-Za-z]{3,}")

_BENGALI_BLOCK = re.compile(r"[ঀ-৿]")


def is_bijoy(text: str) -> bool:
    """Return True if `text` looks like Bijoy-encoded Bengali."""
    if not text or not text.strip():
        return False
    if _BENGALI_BLOCK.search(text):  # already Unicode Bengali
        return False
    if any(ch in _BIJOY_MARKS for ch in text):
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

    try:
        result = _library_converter().convertBijoyToUnicode(text)
    except Exception as exc:  # the library raises bare IndexErrors
        raise ConversionError(f"could not convert {text!r}") from exc

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


def normalize(text: str) -> NormalizedText:
    """Clean one piece of text.

    Unicode Bengali and English pass through (trimmed). Bijoy is converted.
    If conversion fails, the original is kept and the error is recorded, so
    one bad line never stops a whole catalogue from loading.
    """
    original = text
    cleaned = " ".join(text.split())
    if not is_bijoy(cleaned):
        return NormalizedText(cleaned, original, converted=False)
    try:
        return NormalizedText(to_unicode(cleaned), original, converted=True)
    except ConversionError as exc:
        return NormalizedText(cleaned, original, converted=False, error=str(exc))


if __name__ == "__main__":
    # Try it: python -m ha_catalogue.encoding "Kv‡e`yj Bmjvg"
    for arg in sys.argv[1:]:
        result = normalize(arg)
        print(f"{arg}  ->  {result.text}  (converted={result.converted})")
