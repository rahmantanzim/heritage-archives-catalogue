"""Category catalogues (01-35, 37-130, 131-188, 189, 190-242, 250-399, 36 RAB).

Rows are real, shortened where long.
"""

from ha_catalogue.cleaning import Fix
from ha_catalogue.models import IssueKind
from ha_catalogue.readers.category_catalogue import (
    STANDARD,
    TITLE_ONLY,
    WITH_KEPT_AT,
    read_category_catalogue,
)

DISTRICT_BOOKS = """Catalogue #,District/ Topic,Title & Information
189.0 (1)       ,Local History,"মুহা. কামরুজ্জামান, বাংলাদেশের জেলা পরিচিতি, ঢাকা: নান্দনিক, ২০১০। "
189.1.(29A),Bagerhat,"নবনির্মিত মন্দির উদ্বোধন ও প্লাটিনাম জুবিলী স্মারক গ্রন্থ, ২০০৩।"
189.22 (96)    e,Jessore,"বাতায়ন, যশোর সারকারী মহিলা কলেজ বার্ষিকী, ১৯৯৭-৯৮।"
Local History,,
"""


def test_read_district_books(write_csv):
    result = read_category_catalogue(write_csv("books.csv", DISTRICT_BOOKS), STANDARD)

    assert [item.item_id for item in result.items] == ["189.0/1", "189.1/29a", "189.22/96"]
    assert result.items[0].subject == "Local History"
    assert result.items[0].title.endswith("২০১০।")  # trailing space removed
    assert result.items[1].id_original == "189.1.(29A)"

    malformed = [i for i in result.issues if i.kind is IssueKind.MALFORMED_ID]
    assert [i.row for i in malformed] == [4, 5]  # extra "e", then no ID at all


GEOGRAPHY = """Catalogue number,Category,Title & Information
131,Geneology (Also see 220a, 349, 249.95) ,
132 (1) \u00a0,Geography and Enviromental Science,"Sudeepta Adhikari, Political Geography"
,Portrait-253,
191 (2),Manuals (The Bengal Treasury),"MYcÖRvZš¿x evsjv‡`k miKvi"
91c (দ্বাদশ খণ্ড),Encyclopedia of Islamic Foundation,ইসলামী বিশ্বকোষ
CD-01,382-Press Releases  ,1.  Asiatic Society of Bangladesh
,382-Press Releases  ,2.  Basarat Ali
241 (10,Obituaries,Missing bracket
"""


def test_category_catalogue_row_types(write_csv):
    result = read_category_catalogue(write_csv("cat.csv", GEOGRAPHY), STANDARD)

    assert [item.item_id for item in result.items] == [
        "132/1",
        "191/2",
        "91c/দ্বাদশ খণ্ড",  # a volume name as the item number
        "cd/01",
    ]
    assert result.section_headings == 2  # "131" and "Portrait-253"

    bijoy = result.items[1]
    assert bijoy.title == "গণপ্রজাতন্ত্রী বাংলাদেশ সরকার"
    assert Fix.BIJOY_CONVERTED in bijoy.fixes

    cd = result.items[3]
    assert cd.title == "1. Asiatic Society of Bangladesh / 2. Basarat Ali"
    assert cd.subject == "382-Press Releases"

    kinds = [issue.kind for issue in result.issues]
    assert kinds.count(IssueKind.CONTINUATION_ROW) == 1
    assert kinds.count(IssueKind.MALFORMED_ID) == 1  # "241 (10"


def test_kept_at_column_becomes_a_note(write_csv):
    rows = """Catalogue no.,Category,Title & Information ,Kept at
37 (1)\u00a0\u00a0\u00a0 \u00a0,Birds,"শরীফ খান, বাংলাদেশের পাখি",Almirah 3
"""
    result = read_category_catalogue(write_csv("birds.csv", rows), WITH_KEPT_AT)
    assert result.items[0].item_id == "37/1"
    assert result.items[0].notes == "Kept at: Almirah 3"


def test_title_only_biography_list(write_csv):
    rows = """Catalouge Number,"Author, Title & Details",,
36 RAB (1),"রবীন্দ্রসমগ্র, খণ্ড-১, পাঠক সমাবেশ, ২০১১। ",,
"""
    result = read_category_catalogue(write_csv("rab.csv", rows), TITLE_ONLY)
    item = result.items[0]
    assert item.item_id == "36rab/1"
    assert item.title == "রবীন্দ্রসমগ্র, খণ্ড-১, পাঠক সমাবেশ, ২০১১।"
    assert item.subject is None
