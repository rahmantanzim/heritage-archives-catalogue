"""Numbered lists: posters (256) and leaflets (180). Rows are real."""

from ha_catalogue.cleaning import Fix
from ha_catalogue.models import IssueKind
from ha_catalogue.quality import find_duplicate_ids
from ha_catalogue.readers.numbered_list import LEAFLETS, POSTERS, read_numbered_list

POSTER_ROWS = """Poster#,Topics,Publisher,Comments,
1,১৮ অক্টোবর শেখ রাসেল এর জন্মদিন,শিশু অধিকার কমিশন,শেখ রাসেল,
9,ঘবংঃষব ঘওউঙ,ঘবংঃষব,,
,ঞযব ঘধঃরড়হ গধৎঃুৎং সবসড়ৎরধষ ,,,
13,কেন আওয়ামী লীগ কে চাই না,-,-,
,,,,
3476-3500 duvKv  ,,,,
13,দেশের গানের কনসার্ট,চ্যানেল আই,,
"""


def test_read_posters(write_csv):
    result = read_numbered_list(write_csv("posters.csv", POSTER_ROWS), POSTERS)

    assert [item.item_id for item in result.items] == ["256/1", "256/9", "256/13", "256/13"]
    assert result.skipped_empty_rows == 1

    first = result.items[0]
    assert first.publisher == "শিশু অধিকার কমিশন"
    assert first.row == 2

    nido = result.items[1]
    assert nido.title == "Nestle NIDO / The Nation Martyrs memorial"
    assert nido.title_original == "ঘবংঃষব ঘওউঙ"
    assert nido.publisher == "Nestle"
    assert Fix.ENGLISH_RECOVERED in nido.fixes

    assert result.items[2].publisher is None  # "-" means empty

    kinds = [issue.kind for issue in result.issues]
    assert IssueKind.CONTINUATION_ROW in kinds
    assert IssueKind.RESERVED_RANGE in kinds


def test_duplicate_ids_are_reported_and_both_kept(write_csv):
    result = read_numbered_list(write_csv("posters.csv", POSTER_ROWS), POSTERS)
    duplicates = find_duplicate_ids(result.items)
    assert len(duplicates) == 1
    assert duplicates[0].kind is IssueKind.DUPLICATE_ID
    assert duplicates[0].row == 8
    assert sum(item.item_id == "256/13" for item in result.items) == 2


LEAFLET_ROWS = """Number,Topic (বিষয়বস্তু ),Publisher(প্রকাশক),Date (তারিখ)
2,এক মুজিবের রক্ত থেকে লক্ষ মুজিব জন্ম নেবে,বাংলাদশে আওয়ামী লীগ,15-Aug
1901-2000,,,
4656K,কুমিল্লা সিটি কর্পোরেশন নির্বাচন,ওয়ার্ডবাসী,নাই
"""


def test_read_leaflets(write_csv):
    result = read_numbered_list(write_csv("leaflets.csv", LEAFLET_ROWS), LEAFLETS)

    assert [item.item_id for item in result.items] == ["180/2", "180/4656k"]
    assert result.items[0].notes == "Date: 15-Aug"
    assert result.items[1].notes is None  # নাই ("none") means empty
    reserved = [i for i in result.issues if i.kind is IssueKind.RESERVED_RANGE]
    assert [i.value for i in reserved] == ["1901-2000"]
