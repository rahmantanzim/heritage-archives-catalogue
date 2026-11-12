"""Reader for the 36 PC biography index: person -> item.

Columns: "Biography of" (a name) and a catalogue number such as
"36 PC (44)". One item can cover several people, and a row with no name
belongs to the person above it. Rows are grouped into one item per ID,
listing every person it covers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ha_catalogue.cleaning import Fix, clean_cell
from ha_catalogue.ids import parse_catalogue_id
from ha_catalogue.models import CatalogueItem, Issue, IssueKind, ReadResult
from ha_catalogue.readers._common import cell_at, csv_rows, record_cleaning

_TITLE_PREFIX = "Biography of: "


@dataclass
class _Group:
    row: int
    catalogue: str
    number: str
    id_original: str
    people: list[str] = field(default_factory=list)
    fixes: set[Fix] = field(default_factory=set)


def read_biography_index(path: Path) -> ReadResult:
    source = path.name
    result = ReadResult()
    groups: dict[str, _Group] = {}
    current_person: str | None = None

    for row, cells in csv_rows(path):
        name = clean_cell(cell_at(cells, 0))
        raw_id = cell_at(cells, 1)
        record_cleaning(result.issues, source, row, name)

        if not name.text and not raw_id.strip():
            result.skipped_empty_rows += 1
            continue
        if name.text:
            current_person = name.text
        if current_person is None:
            result.issues.append(Issue(source, row, IssueKind.MISSING_ID, "ID with no person"))
            continue

        parsed = parse_catalogue_id(raw_id)
        if parsed is None:
            result.issues.append(
                Issue(source, row, IssueKind.MALFORMED_ID, "unreadable catalogue ID", raw_id)
            )
            continue

        key = f"{parsed.catalogue}/{parsed.number}"
        group = groups.setdefault(key, _Group(row, parsed.catalogue, parsed.number, raw_id.strip()))
        if current_person not in group.people:
            group.people.append(current_person)
        if name.fix is not Fix.NONE:
            group.fixes.add(name.fix)

    for group in groups.values():
        title = _TITLE_PREFIX + "; ".join(group.people)
        result.items.append(
            CatalogueItem(
                source=source,
                row=group.row,
                catalogue=group.catalogue,
                number=group.number,
                id_original=group.id_original,
                title=title,
                title_original=title,
                fixes=tuple(sorted(group.fixes)),
            )
        )
    return result
