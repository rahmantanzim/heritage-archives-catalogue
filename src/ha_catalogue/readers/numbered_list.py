"""Reader for numbered lists: posters (256) and leaflets (180).

Columns: number, topic, publisher, and one more (comments or date).
- A row with no number but some text continues the item above it.
- "1901-2000" (or "3476-3500 ফাঁকা") marks numbers kept blank on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from ha_catalogue.cleaning import clean_cell
from ha_catalogue.ids import parse_plain_number, parse_reserved_range
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
class NumberedList:
    catalogue: str
    last_column_label: str | None  # "Date" for leaflets; None keeps the text as is


POSTERS = NumberedList(catalogue="256", last_column_label=None)
LEAFLETS = NumberedList(catalogue="180", last_column_label="Date")


def read_numbered_list(path: Path, layout: NumberedList) -> ReadResult:
    source = path.name
    result = ReadResult()

    for row, cells in csv_rows(path):
        raw_id = cell_at(cells, 0)
        topic = clean_cell(cell_at(cells, 1))
        publisher = clean_cell(cell_at(cells, 2))
        last = clean_cell(cell_at(cells, 3))
        record_cleaning(result.issues, source, row, topic, publisher, last)
        notes = labelled(layout.last_column_label, last.text)
        has_content = any(c.text for c in (topic, publisher, last))

        if not raw_id.strip():
            if not has_content:
                result.skipped_empty_rows += 1
            elif not result.items:
                result.issues.append(
                    Issue(source, row, IssueKind.MISSING_ID, "text with no number")
                )
            else:
                previous = result.items[-1]
                result.items[-1] = replace(
                    previous,
                    title=join_text(previous.title, topic.text) or previous.title,
                    publisher=join_text(previous.publisher, publisher.text),
                    notes=join_text(previous.notes, notes),
                    fixes=merge_fixes(previous.fixes, fixes_of(topic, publisher, last)),
                )
                result.issues.append(
                    Issue(
                        source,
                        row,
                        IssueKind.CONTINUATION_ROW,
                        f"no number; added to {previous.item_id} above",
                    )
                )
            continue

        number = parse_plain_number(raw_id)
        if number is None:
            reserved = parse_reserved_range(raw_id)
            if reserved and not has_content:
                result.issues.append(
                    Issue(
                        source,
                        row,
                        IssueKind.RESERVED_RANGE,
                        f"numbers {reserved[0]}-{reserved[1]} kept blank",
                        raw_id.strip(),
                    )
                )
            else:
                result.issues.append(
                    Issue(source, row, IssueKind.MALFORMED_ID, "unreadable number", raw_id)
                )
            continue

        if not topic.text:
            result.issues.append(Issue(source, row, IssueKind.SUSPECT_ROW, "item has no topic"))

        result.items.append(
            CatalogueItem(
                source=source,
                row=row,
                catalogue=layout.catalogue,
                number=number,
                id_original=raw_id,
                title=topic.text or "",
                title_original=topic.original,
                publisher=publisher.text,
                notes=notes,
                fixes=fixes_of(topic, publisher, last),
            )
        )

    return result
