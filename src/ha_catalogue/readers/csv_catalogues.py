"""Readers for the three Unicode CSV catalogues.

- Catalogue 256: posters        (Poster#, Topics, Publisher, Comments)
- Catalogue 189: district books (Catalogue #, District/ Topic, Title & Information)
- Catalogue 00:  subject index  (Title, Reference)

Readers never stop on a bad row. They keep what they can and record an Issue.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

from ha_catalogue.cleaning import CleanCell, Fix, clean_cell
from ha_catalogue.ids import (
    find_catalogue_references,
    parse_catalogue_id,
    parse_plain_number,
    parse_reserved_range,
)
from ha_catalogue.models import CatalogueItem, Issue, IssueKind, ReadResult, SubjectEntry

POSTER_CATALOGUE = "256"


def _rows(path: Path) -> Iterator[tuple[int, list[str]]]:
    """Yield (row_number, cells) for each data row. The header is row 1."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        yield from enumerate(reader, start=2)


def _cell(cells: list[str], index: int) -> str:
    return cells[index] if index < len(cells) else ""


def _record_cleaning(issues: list[Issue], source: str, row: int, cell: CleanCell) -> None:
    if cell.error:
        issues.append(Issue(source, row, IssueKind.CONVERSION_FAILED, cell.error, cell.original))
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


def _fixes(*cells: CleanCell) -> tuple[Fix, ...]:
    return tuple(sorted({c.fix for c in cells if c.fix is not Fix.NONE}))


def _join(first: str | None, second: str | None) -> str | None:
    if first and second:
        return f"{first} / {second}"
    return first or second


# --- Posters (catalogue 256) ----------------------------------------------


def read_posters(path: Path) -> ReadResult:
    source = path.name
    result = ReadResult()

    for row, cells in _rows(path):
        raw_id = _cell(cells, 0)
        topic = clean_cell(_cell(cells, 1))
        publisher = clean_cell(_cell(cells, 2))
        comments = clean_cell(_cell(cells, 3))
        for cell in (topic, publisher, comments):
            _record_cleaning(result.issues, source, row, cell)

        has_content = any(c.text for c in (topic, publisher, comments))
        number = parse_plain_number(raw_id)

        if number is None and not raw_id.strip():
            if not has_content:
                result.skipped_empty_rows += 1
                continue
            # A row with no ID but some text continues the poster above it.
            if not result.items:
                result.issues.append(
                    Issue(source, row, IssueKind.MISSING_ID, "text with no poster number")
                )
                continue
            previous = result.items[-1]
            result.items[-1] = replace(
                previous,
                title=_join(previous.title, topic.text) or previous.title,
                publisher=_join(previous.publisher, publisher.text),
                notes=_join(previous.notes, comments.text),
                fixes=tuple(sorted(set(previous.fixes) | set(_fixes(topic, publisher, comments)))),
            )
            result.issues.append(
                Issue(
                    source,
                    row,
                    IssueKind.CONTINUATION_ROW,
                    f"no poster number; added to poster {previous.number} above",
                )
            )
            continue

        if number is None:
            reserved = parse_reserved_range(raw_id)
            if reserved:
                result.issues.append(
                    Issue(
                        source,
                        row,
                        IssueKind.RESERVED_RANGE,
                        f"numbers {reserved[0]}-{reserved[1]} marked blank",
                        raw_id.strip(),
                    )
                )
            else:
                result.issues.append(
                    Issue(source, row, IssueKind.MALFORMED_ID, "unreadable poster number", raw_id)
                )
            continue

        if not topic.text:
            result.issues.append(Issue(source, row, IssueKind.SUSPECT_ROW, "poster has no topic"))

        result.items.append(
            CatalogueItem(
                source=source,
                row=row,
                catalogue=POSTER_CATALOGUE,
                number=number,
                id_original=raw_id,
                title=topic.text or "",
                title_original=topic.original,
                publisher=publisher.text,
                notes=comments.text,
                fixes=_fixes(topic, publisher, comments),
            )
        )

    return result


# --- District books (catalogue 189) ---------------------------------------


def read_district_books(path: Path) -> ReadResult:
    source = path.name
    result = ReadResult()

    for row, cells in _rows(path):
        raw_id = _cell(cells, 0)
        district = clean_cell(_cell(cells, 1))
        title = clean_cell(_cell(cells, 2))
        for cell in (district, title):
            _record_cleaning(result.issues, source, row, cell)

        if not raw_id.strip() and not district.text and not title.text:
            result.skipped_empty_rows += 1
            continue

        parsed = parse_catalogue_id(raw_id)
        if parsed is None:
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
            result.issues.append(Issue(source, row, IssueKind.SUSPECT_ROW, "book has no title"))

        result.items.append(
            CatalogueItem(
                source=source,
                row=row,
                catalogue=parsed.catalogue,
                number=parsed.number,
                id_original=raw_id,
                title=title.text or "",
                title_original=title.original,
                subject=district.text,
                fixes=_fixes(district, title),
            )
        )

    return result


# --- Subject index (catalogue 00) -----------------------------------------

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

    for row, cells in _rows(path):
        term = " ".join(_cell(cells, 0).split())
        reference = " ".join(_cell(cells, 1).split())
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
