"""English that was wrongly turned into Bengali letters (catalogue 256)."""

import pytest

from ha_catalogue.garbled_english import recover_english


@pytest.mark.parametrize(
    ("garbled", "english"),
    [
        ("ঘবংঃষব ঘওউঙ", "Nestle NIDO"),
        ("জধলংযধযর টহরাবৎংরঃু", "Rajshahi University"),
        ("ঈযধশসধ, গধৎসধ, ধহফ ঞৎরঢ়ঁৎধ", "Chakma, Marma, and Tripura"),
        ("কঁধষধ খঁসঢ়ঁৎ ঈড়হাবহঃরড়হ ঈবহঃবৎ", "Kuala Lumpur Convention Center"),
        # The converter moved "w" after the next letter; we move it back.
        ("ঝযড়রিহম ঃযব ঈড়ঁহঃৎু ঃড় রঃং চবড়ঢ়ষব", "Showing the Country to its People"),
        ("ঘবংিঢ়ধঢ়বৎ", "Newspaper"),
    ],
)
def test_recovers_english(garbled, english):
    assert recover_english(garbled) == english


@pytest.mark.parametrize(
    "bengali",
    [
        "রাজশাহী",
        "ফুটবল",
        "বিবাহ",
        "চারুকলা বিভাগ, রা. বি.",
        "শিশু অধিকার কমিশন",
        "বিলু কবীর, বাংলাদেশের জেলা নামকরণের ইতিহাস, ঢাকা: গতিধারা, ২০১০।",
    ],
)
def test_leaves_real_bengali_alone(bengali):
    assert recover_english(bengali) is None


def test_ignores_plain_english():
    assert recover_english("Rajshahi University") is None
