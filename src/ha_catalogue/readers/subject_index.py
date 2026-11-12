"""Reader for the Main List subject index (catalogue 00): term -> catalogues.

Example rows: "Abortion | (See Family Planning 104)", "Animals | 11 also see
cattle 52". Some terms were split in two at a hyphen ("Anti | corruption -74",
originally "Anti-corruption -74"); those are rejoined and reported.
"""

from __future__ import annotations

import re
from pathlib import Path

from ha_catalogue.ids import find_catalogue_references
from ha_catalogue.models import Issue, IssueKind, ReadResult, SubjectEntry
from ha_catalogue.readers._common import cell_at, csv_rows

# Some terms were split in two at a hyphen, e.g. "Anti" | "corruption -74"
# (was "Anti-corruption -74") or "Hair" | "dressing (see 75)".
_SPLIT_BEFORE_NUMBER = re.compile(r"^(?P<word>[a-z][\w &]*?)\s*-\s*(?P<ref>\d.*)$")
_SPLIT_BEFORE_PAREN = re.compile(r"^(?P<word>[a-z]\w*)\s+(?P<ref>\(.*)$")


def _repair_split(term: str, reference: str) -> tuple[str, str] | None:
    for pattern in (_SPLIT_BEFORE_NUMBER, _SPLIT_BEFORE_PAREN):
        match = pattern.match(reference)
        if match:
            return f"{term}-{match['word']}", match["ref"]
    return None


def read_subject_index(path: Path) -> ReadResult:
    source = path.name
    result = ReadResult()

    for row, cells in csv_rows(path):
        term = " ".join(cell_at(cells, 0).split())
        reference = " ".join(cell_at(cells, 1).split())
        if not term and not reference:
            result.skipped_empty_rows += 1
            continue

        repaired = _repair_split(term, reference)
        if repaired:
            result.issues.append(
                Issue(
                    source,
                    row,
                    IssueKind.SPLIT_ROW_REPAIRED,
                    f"joined as {repaired[0]!r}",
                    f"{term} | {reference}",
                )
            )
            term, reference = repaired
        elif reference[:1].islower() or term.count("(") != term.count(")"):
            result.issues.append(
                Issue(
                    source,
                    row,
                    IssueKind.SUSPECT_ROW,
                    "term or reference looks cut in the wrong place",
                    f"{term} | {reference}",
                )
            )

        catalogues = find_catalogue_references(reference)
        if not catalogues:
            result.issues.append(
                Issue(
                    source,
                    row,
                    IssueKind.MISSING_REFERENCE,
                    "no catalogue number",
                    f"{term} | {reference}",
                )
            )

        result.subjects.append(SubjectEntry(source, row, term, reference, catalogues))

    return result
