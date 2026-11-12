"""Recover English text that was wrongly converted into Bengali letters.

Some catalogue cells were English (e.g. "Rajshahi University"), but at some
point every cell went through a Bijoy-to-Unicode converter, English included.
Each English letter became a Bengali letter, giving "জধলংযধযর টহরাবৎংরঃু".

The mistake can be run backwards: we know which Bengali letter each English
letter turns into, so we map them back. We only accept the result when it
clearly reads as English. Real Bengali such as "রাজশাহী" also maps to Latin
letters ("ivRkvnx"), but that result fails the English checks below and is
left alone.
"""

from __future__ import annotations

import re
import string
from functools import lru_cache

from bijoy2unicode import converter

from ha_catalogue.english import reads_as_english

_BENGALI = re.compile("[\u0980-\u09ff]")
_BENGALI_LETTER = re.compile("[\u0985-\u09b9\u09dc-\u09df]")  # অ-হ, ড়-য়
_ASCII_LETTER = re.compile("[A-Za-z]")
_I_KAR = "\u09bf"  # ি — the converter moved it after the next letter


@lru_cache(maxsize=1)
def _bengali_to_latin() -> dict[str, str]:
    """Build the reverse map from the converter's own letter table."""
    lib = converter.Unicode()
    mapping: dict[str, str] = {}
    for letter in string.ascii_letters:
        bengali = lib.convertBijoyToUnicode(letter)
        if bengali != letter:
            mapping.setdefault(bengali, letter)
    # Both "y" and "z" become ু (U+09C1). "y" is far more common in English.
    mapping["\u09c1"] = "y"
    # ড় ঢ় য় can also be stored as letter + nukta dot (U+09BC).
    mapping["\u09a1\u09bc"] = "o"
    mapping["\u09a2\u09bc"] = "p"
    mapping["\u09af\u09bc"] = "q"
    # Digits were converted too: "3rd" became "৩ৎফ". ০ is U+09E6.
    for digit in range(10):
        mapping[chr(0x09E6 + digit)] = str(digit)
    return mapping


def _reverse(text: str) -> str:
    mapping = _bengali_to_latin()
    keys = sorted(mapping, key=len, reverse=True)
    out: list[str] = []
    i = 0
    while i < len(text):
        for key in keys:
            if text.startswith(key, i):
                latin = mapping[key]
                i += len(key)
                # "Newspaper" came out as ঘবংি: the ি ("w") was moved after
                # "s". If ি follows a letter, the "w" belongs before it.
                if text.startswith(_I_KAR, i) and key != _I_KAR:
                    out.append("w")
                    i += len(_I_KAR)
                out.append(latin)
                break
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def recover_english(text: str) -> str | None:
    """Return the original English if `text` is garbled English, else None."""
    # The converter garbled whole cells. Real English letters next to the
    # Bengali ("Art and Artist অভিধান") mean the Bengali is real Bengali.
    if _ASCII_LETTER.search(text):
        return None
    # Bengali digits alone ("২১০৭") are not evidence of garbled English.
    if not _BENGALI_LETTER.search(text):
        return None
    candidate = _reverse(text.strip())
    if _BENGALI.search(candidate):  # some letters had no English source
        return None
    return candidate if reads_as_english(candidate) else None
