"""Reader tests use small CSV files made from real catalogue rows."""

from pathlib import Path

from ha_catalogue.cleaning import Fix
from ha_catalogue.models import IssueKind
from ha_catalogue.quality import find_duplicate_ids
from ha_catalogue.readers.csv_catalogues import (
    read_district_books,
    read_posters,
    read_subject_index,
)


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text("﻿" + text, encoding="utf-8")
    return path


def _kinds(result):
    return [issue.kind for issue in result.issues]


POSTERS = """Poster#,Topics,Publisher,Comments,
1,১৮ অক্টোবর শেখ রাসেল এর জন্মদিন,শিশু অধিকার কমিশন,শেখ রাসেল,
9,ঘবংঃষব ঘওউঙ,ঘবংঃষব,,
,ঞযব ঘধঃরড়হ গধৎঃুৎং সবসড়ৎরধষ ,,,
13,কেন আওয়ামী লীগ কে চাই না,-,-,
,,,,
3476-3500 duvKv  ,,,,
13,দেশের গানের কনসার্ট,চ্যানেল আই,,
"""


def test_read_posters(tmp_path):
    result = read_posters(_write(tmp_path, "posters.csv", POSTERS))

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

    # "-" means empty
    assert result.items[2].publisher is None

    kinds = _kinds(result)
    assert IssueKind.CONTINUATION_ROW in kinds
    assert IssueKind.RESERVED_RANGE in kinds


def test_duplicate_ids_are_reported_and_both_kept(tmp_path):
    result = read_posters(_write(tmp_path, "posters.csv", POSTERS))
    duplicates = find_duplicate_ids(result.items)
    assert len(duplicates) == 1
    assert duplicates[0].kind is IssueKind.DUPLICATE_ID
    assert duplicates[0].row == 8
    assert sum(item.item_id == "256/13" for item in result.items) == 2


DISTRICT_BOOKS = """Catalogue #,District/ Topic,Title & Information
189.0 (1)       ,Local History,"মুহা. কামরুজ্জামান, বাংলাদেশের জেলা পরিচিতি, ঢাকা: নান্দনিক, ২০১০। "
189.1.(29A),Bagerhat,"নবনির্মিত মন্দির উদ্বোধন ও প্লাটিনাম জুবিলী স্মারক গ্রন্থ, ২০০৩।"
189.22 (96)    e,Jessore,"বাতায়ন, যশোর সারকারী মহিলা কলেজ বার্ষিকী, ১৯৯৭-৯৮।"
Local History,,
"""


def test_read_district_books(tmp_path):
    result = read_district_books(_write(tmp_path, "books.csv", DISTRICT_BOOKS))

    assert [item.item_id for item in result.items] == ["189.0/1", "189.1/29a", "189.22/96"]
    assert result.items[0].subject == "Local History"
    assert result.items[0].title.endswith("২০১০।")  # trailing space removed
    assert result.items[1].id_original == "189.1.(29A)"

    malformed = [i for i in result.issues if i.kind is IssueKind.MALFORMED_ID]
    assert [i.row for i in malformed] == [4, 5]  # extra "e", then no ID at all


SUBJECTS = """Title,Reference
Abortion,(See Family Planning 104)
Anti,corruption -74
Hair,dressing (see 75)
Astrology,(See ........ )
Also,"see 01, 65, 83"
"""


def test_read_subject_index(tmp_path):
    result = read_subject_index(_write(tmp_path, "main.csv", SUBJECTS))
    terms = {s.term: s for s in result.subjects}

    assert terms["Abortion"].catalogues == ("104",)
    assert terms["Anti-corruption"].catalogues == ("74",)
    assert terms["Hair-dressing"].reference == "(see 75)"

    kinds = _kinds(result)
    assert kinds.count(IssueKind.SPLIT_ROW_REPAIRED) == 2
    assert IssueKind.MISSING_REFERENCE in kinds  # Astrology
    assert IssueKind.SUSPECT_ROW in kinds  # "Also | see 01, ..."
