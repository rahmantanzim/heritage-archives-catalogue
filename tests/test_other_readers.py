"""Theses (82), the 36 PC biography index, and the subject index (00)."""

from ha_catalogue.models import IssueKind
from ha_catalogue.readers.biography_index import read_biography_index
from ha_catalogue.readers.subject_index import read_subject_index
from ha_catalogue.readers.theses import read_theses

THESES = """Degree,Researcher,Thesis topic,Supervisor,Year,Institute,Catalogue Number
Ph.D,আবু মো.ইকবাল রুমি শাহ্,১৯৪৩ সালের দুর্ভিক্ষ,ড.নূরুল হোসেন চৌধুরী,1998,"ইতিহাস বিভাগ, রা.বি.",82.1
M.Phil,এ টি এম কাউছার হোসেন,গণসঙ্গীত,ড. মুনতাসীর মামুন,2002,গবেষণা ইনস্টিটিউট,400.17 (152)  [82.148]
Ph.D,Someone,No number,,,,
"""


def test_read_theses(write_csv):
    result = read_theses(write_csv("theses.csv", THESES))

    assert [item.item_id for item in result.items] == ["82/1", "82/148"]
    first = result.items[0]
    assert first.subject == "Ph.D"
    assert first.publisher == "ইতিহাস বিভাগ, রা.বি."
    assert first.notes == "Researcher: আবু মো.ইকবাল রুমি শাহ্; Supervisor: ড.নূরুল হোসেন চৌধুরী; Year: 1998"
    assert result.items[1].notes.endswith("Also filed as: 400.17 (152)")
    assert [i.kind for i in result.issues] == [IssueKind.MALFORMED_ID]


BIOGRAPHY_INDEX = """Biography of,Catalogue number
A B M Musa,36 PC (44)
A B M Musa,36 PC (100)
,36 PC (477)
A R Mallick,36 PC (44)
"""


def test_biography_index_groups_people_by_item(write_csv):
    result = read_biography_index(write_csv("pc.csv", BIOGRAPHY_INDEX))

    titles = {item.item_id: item.title for item in result.items}
    assert titles == {
        "36pc/44": "Biography of: A B M Musa; A R Mallick",
        "36pc/100": "Biography of: A B M Musa",
        "36pc/477": "Biography of: A B M Musa",  # no name: the person above
    }
    assert result.issues == []


SUBJECTS = """Title,Reference
Abortion,(See Family Planning 104)
Anti,corruption -74
Hair,dressing (see 75)
Astrology,(See ........ )
Also,"see 01, 65, 83"
"""


def test_read_subject_index(write_csv):
    result = read_subject_index(write_csv("main.csv", SUBJECTS))
    terms = {s.term: s for s in result.subjects}

    assert terms["Abortion"].catalogues == ("104",)
    assert terms["Anti-corruption"].catalogues == ("74",)
    assert terms["Hair-dressing"].reference == "(see 75)"

    kinds = [issue.kind for issue in result.issues]
    assert kinds.count(IssueKind.SPLIT_ROW_REPAIRED) == 2
    assert IssueKind.MISSING_REFERENCE in kinds  # Astrology
    assert IssueKind.SUSPECT_ROW in kinds  # "Also | see 01, ..."
