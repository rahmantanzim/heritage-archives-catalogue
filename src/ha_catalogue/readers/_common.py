"""Helpers shared by every CSV reader."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

from ha_catalogue.cleaning import CleanCell, Fix
from ha_catalogue.models import Issue, IssueKind


def csv_rows(path: Path) -> Iterator[tuple[int, list[str]]]:
    """Yield (row_number, cells) for each data row. The header is row 1."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        yield from enumerate(reader, start=2)


def cell_at(cells: list[str], index: int | None) -> str:
    """The cell at `index`, or "" if the row is short or there is no column."""
    if index is None or index >= len(cells):
        return ""
    return cells[index]


def record_cleaning(issues: list[Issue], source: str, row: int, *cells: CleanCell) -> None:
    """Add an issue for every cell that failed to convert or was recovered."""
    for cell in cells:
        if cell.error:
            issues.append(
                Issue(source, row, IssueKind.CONVERSION_FAILED, cell.error, cell.original)
            )
        if cell.fix is Fix.ENGLISH_RECOVERED:
            issues.append(
                Issue(
                    source,
                    row,
                    IssueKind.ENGLISH_RECOVERED,
                    f"recovered as {cell.text!r}",
                    cell.original.strip(),
                )
            )


def fixes_of(*cells: CleanCell) -> tuple[Fix, ...]:
    return tuple(sorted({c.fix for c in cells if c.fix is not Fix.NONE}))


def merge_fixes(first: tuple[Fix, ...], second: tuple[Fix, ...]) -> tuple[Fix, ...]:
    return tuple(sorted(set(first) | set(second)))


def join_text(first: str | None, second: str | None) -> str | None:
    """Join two optional texts with " / ", keeping whichever exists."""
    if first and second:
        return f"{first} / {second}"
    return first or second


def labelled(label: str | None, text: str | None) -> str | None:
    """ "Kept at: Almirah 3" style notes. No label: the text alone."""
    if not text:
        return None
    return f"{label}: {text}" if label else text
