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

from ha_catalogue.english import reads_as_english

_BENGALI = re.compile(r"[ঀ-৿]")
_I_KAR = "ি"  # ি — the converter moved it after the next letter


@lru_cache(maxsize=1)
def _bengali_to_latin() -> dict[str, str]:
    """Build the reverse map from the converter's own letter table."""
    from bijoy2unicode import converter

    lib = converter.Unicode()
    mapping: dict[str, str] = {}
    for letter in string.ascii_letters:
        bengali = lib.convertBijoyToUnicode(letter)
        if bengali != letter:
            mapping.setdefault(bengali, letter)
    # Both "y" and "z" become ু. "y" is far more common in English.
    mapping["ু"] = "y"
    # ড়, ঢ়, য় can be stored as one character or as letter + dot (়).
    mapping["ড়"] = "o"
    mapping["ঢ়"] = "p"
    mapping["য়"] = "q"
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
    if not _BENGALI.search(text):
        return None
    candidate = _reverse(text.strip())
    if _BENGALI.search(candidate):  # some letters had no English source
        return None
    return candidate if reads_as_english(candidate) else None
