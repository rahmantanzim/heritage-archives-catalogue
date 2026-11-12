"""A simple test for "does this Latin text read as English?".

Used in two places:
- to recover English that was garbled into Bengali letters
- to leave English sections alone inside a mostly-Bijoy cell

Bijoy text is also Latin letters ("evsjv‡`k"), so we can't just check the
alphabet. Instead we look at how English is built: a normal share of vowels,
every longer word has a vowel, and few of the letters Bijoy uses for vowel
signs (v = া, w = ি, x = ী).
"""

from __future__ import annotations

import re

_WORD3 = re.compile(r"[A-Za-z]{3,}")
_VOWEL = re.compile(r"[aeiouyAEIOUY]")
_MIXED_CASE = re.compile(r"[a-z][A-Z]")

_MIN_LETTERS = 3
_VOWEL_SHARE = (0.2, 0.7)
_MAX_VOWEL_SIGN_LETTER_SHARE = 0.12


def reads_as_english(text: str) -> bool:
    letters = [ch for ch in text if ch.isascii() and ch.isalpha()]
    if len(letters) < _MIN_LETTERS:
        return False
    vowel_share = sum(bool(_VOWEL.match(ch)) for ch in letters) / len(letters)
    if not _VOWEL_SHARE[0] <= vowel_share <= _VOWEL_SHARE[1]:
        return False
    if sum(ch in "vwx" for ch in letters) / len(letters) >= _MAX_VOWEL_SIGN_LETTER_SHARE:
        return False
    words = _WORD3.findall(text)
    if any(_MIXED_CASE.search(word) for word in words):
        return False
    return all(_VOWEL.search(word) for word in words)
