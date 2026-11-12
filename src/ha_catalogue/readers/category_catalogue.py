"""Reader for category catalogues: ID, category, title (+ optional extras).

Used by most catalogue files (01-35, 37-130, 131-188, 189, 190-242,
250-399) and, with no category column, by the biography lists (36 RAB,
36 NAZ, 36.4).

Row types:
- "132 (1)", "36 RAB (1)", "CD-01"  -> an item
- "131" or "78.1" (no item number)  -> a section heading, not an item
- no ID, only a category            -> a section heading
- no ID, but a title                -> continues the item above it
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from ha_catalogue.cleaning import clean_cell
from ha_catalogue.ids import is_heading_id, parse_catalogue_id, parse_series_id
from ha_catalogue.models import CatalogueItem, Issue, IssueKind, ReadResult
from ha_catalogue.readers._common import (
    cell_at,
    csv_rows,
    fixes_of,
    join_text,
    labelled,
    merge_fixes,
    record_cleaning,
)


@dataclass(frozen=True)
class CategoryColumns:
    """Which column holds what. Column numbers start at 0."""

    id: int = 0
    category: int | None = 1
    title: int = 2
    extra: tuple[tuple[int, str], ...] = ()  # (column, label), e.g. ((3, "Kept at"),)


STANDARD = CategoryColumns()
WITH_KEPT_AT = CategoryColumns(extra=((3, "Kept at"),))
TITLE_ONLY = CategoryColumns(category=None, title=1)


def read_category_catalogue(path: Path, columns: CategoryColumns = STANDARD) -> ReadResult:
    source = path.name
    result = ReadResult()

    for row, cells in csv_rows(path):
        raw_id = cell_at(cells, columns.id)
        category = clean_cell(cell_at(cells, columns.category))
        title = clean_cell(cell_at(cells, columns.title))
        extras = [(label, clean_cell(cell_at(cells, index))) for index, label in columns.extra]
        record_cleaning(result.issues, source, row, category, title, *(c for _, c in extras))

        notes = None
        for label, cell in extras:
            notes = join_text(notes, labelled(label, cell.text))
        all_fixes = fixes_of(category, title, *(c for _, c in extras))

        if not raw_id.strip():
            if not title.text and not notes:
                if category.text:
                    result.section_headings += 1
                else:
                    result.skipped_empty_rows += 1
            elif not result.items:
                result.issues.append(Issue(source, row, IssueKind.MISSING_ID, "text with no ID"))
            else:
                previous = result.items[-1]
                result.items[-1] = replace(
                    previous,
                    title=join_text(previous.title, title.text) or previous.title,
                    notes=join_text(previous.notes, notes),
                    fixes=merge_fixes(previous.fixes, all_fixes),
                )
                result.issues.append(
                    Issue(
                        source,
                        row,
                        IssueKind.CONTINUATION_ROW,
                        f"no ID; added to {previous.item_id} above",
                    )
                )
            continue

        parsed = parse_catalogue_id(raw_id) or parse_series_id(raw_id)
        if parsed is None:
            if is_heading_id(raw_id):
                result.section_headings += 1
            else:
                result.issues.append(
                    Issue(source, row, IssueKind.MALFORMED_ID, "unreadable catalogue ID", raw_id)
                )
            continue

        if parsed.leftover:
            result.issues.append(
                Issue(
                    source,
                    row,
                    IssueKind.MALFORMED_ID,
                    f"extra text after ID: {parsed.leftover!r}",
                    raw_id,
                )
            )
        if not title.text:
            result.issues.append(Issue(source, row, IssueKind.SUSPECT_ROW, "item has no title"))

        result.items.append(
            CatalogueItem(
                source=source,
                row=row,
                catalogue=parsed.catalogue,
                number=parsed.number,
                id_original=raw_id,
                title=title.text or "",
                title_original=title.original,
                subject=category.text,
                notes=notes,
                fixes=all_fixes,
            )
        )

    return result
