"""The records every reader produces, whatever the source format."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ha_catalogue.cleaning import Fix


@dataclass(frozen=True)
class CatalogueItem:
    """One item in the archive, e.g. one poster or one book."""

    source: str  # file name it came from
    row: int  # row number in that file (header is row 1)
    catalogue: str  # e.g. "256", "189.13"
    number: str  # item number inside the catalogue, e.g. "527", "29a"
    id_original: str  # the ID exactly as written in the source
    title: str
    title_original: str
    subject: str | None = None  # topic or district
    publisher: str | None = None
    notes: str | None = None
    fixes: tuple[Fix, ...] = ()  # cleaning applied to any field

    @property
    def item_id(self) -> str:
        """Standard ID used everywhere else, e.g. "189.13/527"."""
        return f"{self.catalogue}/{self.number}"


@dataclass(frozen=True)
class SubjectEntry:
    """One line of the Main List subject index (catalogue 00)."""

    source: str
    row: int
    term: str  # e.g. "Abortion"
    reference: str  # e.g. "(See Family Planning 104)"
    catalogues: tuple[str, ...]  # catalogue numbers mentioned, e.g. ("104",)


class IssueKind(StrEnum):
    MISSING_ID = "missing_id"
    MALFORMED_ID = "malformed_id"
    DUPLICATE_ID = "duplicate_id"
    RESERVED_RANGE = "reserved_range"
    CONTINUATION_ROW = "continuation_row"
    CONVERSION_FAILED = "conversion_failed"
    ENGLISH_RECOVERED = "english_recovered"
    MISSING_REFERENCE = "missing_reference"
    SPLIT_ROW_REPAIRED = "split_row_repaired"
    SUSPECT_ROW = "suspect_row"


@dataclass(frozen=True)
class Issue:
    """A data-quality problem found while reading. Never fatal."""

    source: str
    row: int
    kind: IssueKind
    detail: str
    value: str = ""


@dataclass
class ReadResult:
    items: list[CatalogueItem] = field(default_factory=list)
    subjects: list[SubjectEntry] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    skipped_empty_rows: int = 0
