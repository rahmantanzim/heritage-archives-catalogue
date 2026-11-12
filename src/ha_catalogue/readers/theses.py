"""Reader for catalogue 82: MPhil and PhD theses.

Columns: degree, researcher, thesis topic, supervisor, year, institute,
catalogue number. The number is "82.1", "[82.148]", or a cross-listing
such as "400.17 (152)  [82.148]" (also filed under 400.17).
"""

from __future__ import annotations

import re
from pathlib import Path

from ha_catalogue.cleaning import clean_cell
from ha_catalogue.ids import clean_id
from ha_catalogue.models import CatalogueItem, Issue, IssueKind, ReadResult
from ha_catalogue.readers._common import cell_at, csv_rows, fixes_of, labelled, record_cleaning

THESES_CATALOGUE = "82"

_THESIS_NUMBER = re.compile(r"\[?\s*82\.(?P<number>\d+[a-zA-Z]?)\s*\]?")
_CROSS_LISTING = re.compile(r"^(?P<other>\d+(?:\.\d+)*\s*\(\s*\d+[a-zA-Z]?\s*\))")


def read_theses(path: Path) -> ReadResult:
    source = path.name
    result = ReadResult()

    for row, cells in csv_rows(path):
        degree, researcher, topic, supervisor, year, institute = (
            clean_cell(cell_at(cells, index)) for index in range(6)
        )
        raw_id = cell_at(cells, 6)
        record_cleaning(
            result.issues, source, row, degree, researcher, topic, supervisor, year, institute
        )

        if not raw_id.strip() and not topic.text and not researcher.text:
            result.skipped_empty_rows += 1
            continue

        match = _THESIS_NUMBER.search(clean_id(raw_id))
        if match is None:
            result.issues.append(
                Issue(source, row, IssueKind.MALFORMED_ID, "unreadable thesis number", raw_id)
            )
            continue
        if not topic.text:
            result.issues.append(Issue(source, row, IssueKind.SUSPECT_ROW, "thesis has no topic"))

        cross = _CROSS_LISTING.match(clean_id(raw_id))
        notes_parts = [
            labelled("Researcher", researcher.text),
            labelled("Supervisor", supervisor.text),
            labelled("Year", year.text),
            labelled("Also filed as", cross["other"] if cross else None),
        ]
        result.items.append(
            CatalogueItem(
                source=source,
                row=row,
                catalogue=THESES_CATALOGUE,
                number=match["number"].lower(),
                id_original=raw_id,
                title=topic.text or "",
                title_original=topic.original,
                subject=degree.text,
                publisher=institute.text,
                notes="; ".join(part for part in notes_parts if part) or None,
                fixes=fixes_of(degree, researcher, topic, supervisor, year, institute),
            )
        )

    return result
