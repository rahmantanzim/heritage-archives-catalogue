"""Tests for Bijoy detection and conversion.

Every Bijoy example below comes from a real Heritage Archives catalogue.
"""

import pytest

from ha_catalogue.encoding import is_bijoy, normalize, to_unicode

# --- Detection ---


@pytest.mark.parametrize(
    "text",
    [
        "Kv‡e`yj Bmjvg, evsjv‡`‡ki cÖkvmwbK ms¯‹vi I cybwe©b¨vm 1947-2017, 2019|",
        "AvRKvj",
        "duvKv",  # ফাঁকা ("empty"), found inside a poster ID cell
        "RyjvB-AvM÷, 2019",
    ],
)
def test_detects_bijoy(text):
    assert is_bijoy(text)


@pytest.mark.parametrize(
    "text",
    [
        "The Muslim Family Laws Ordinance, 1961 (Ordinance VIII of 1961)-C-2",
        "Calcutta Review J. 2013 (also see 404.5)",
        "Shureswar (1396)",
        "Bangladesh in Maps, University of Dacca, Dacca Bangladesh.",
        "USIS 2034",
        "বিলু কবীর, বাংলাদেশের জেলা নামকরণের ইতিহাস, ঢাকা: গতিধারা, ২০১০।",
        "",
        "   ",
        "243.3211",
    ],
)
def test_leaves_english_and_unicode_alone(text):
    assert not is_bijoy(text)


# --- Conversion ---


@pytest.mark.parametrize(
    ("bijoy", "expected"),
    [
        ("Kv‡e`yj Bmjvg", "কাবেদুল ইসলাম"),
        ("gvbwP‡Î †Kgb Avgvi evsjv‡`k", "মানচিত্রে কেমন আমার বাংলাদেশ"),
        ("Avey mvC` †PŠayix", "আবু সাঈদ চৌধুরী"),
        # Reph (র্) cases the library alone gets wrong
        ("wbe©vPb", "নির্বাচন"),
        ("cybwe©b¨vm", "পুনর্বিন্যাস"),
        ("Awc©Z", "অর্পিত"),
        ("evwl©Kx", "বার্ষিকী"),
        ("Kg©x", "কর্মী"),
        ("ag©", "ধর্ম"),  # reph at the end used to crash the library
        # Characters the library maps wrongly
        ("iÿYv‡eÿY", "রক্ষণাবেক্ষণ"),
        ("byiæj", "নুরুল"),
        ("AvšÍR©vwZK", "আন্তর্জাতিক"),
        ("mxgvšÍ", "সীমান্ত"),
    ],
)
def test_converts_bijoy(bijoy, expected):
    assert to_unicode(bijoy) == expected


def test_normalize_converts_and_keeps_original():
    result = normalize("  Kv‡e`yj   Bmjvg ")
    assert result.text == "কাবেদুল ইসলাম"
    assert result.converted
    assert result.original == "  Kv‡e`yj   Bmjvg "
    assert result.error is None


def test_normalize_passes_english_through():
    result = normalize(" The Police Act, 1861 ")
    assert result.text == "The Police Act, 1861"
    assert not result.converted
