"""Search the catalogue.

A search matches text anywhere in an item's ID, title, subject, publisher
or notes. If the search words are also a term in the subject index (for
example "Posters" -> catalogue 256), every item in those catalogues
matches too, listed after the direct text matches.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement, case, false, func, or_, select
from sqlalchemy.orm import Session

from ha_catalogue.db import IssueRow, ItemRow, SubjectRow
from ha_catalogue.text import search_key

_LIKE_ESCAPE = "\\"


@dataclass(frozen=True)
class SearchQuery:
    text: str | None = None
    catalogue: str | None = None  # "189" also covers "189.13" etc.
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class SearchPage:
    total: int
    items: list[ItemRow]
    subject_catalogues: tuple[str, ...]  # catalogues added via the subject index


def escape_like(text: str) -> str:
    """Make %, _ and \\ match themselves in a LIKE pattern."""
    for char in (_LIKE_ESCAPE, "%", "_"):
        text = text.replace(char, _LIKE_ESCAPE + char)
    return text


def _in_catalogue(catalogue: str) -> ColumnElement[bool]:
    """Match the catalogue itself and its sub-catalogues (189 -> 189.13)."""
    return or_(
        ItemRow.catalogue == catalogue,
        ItemRow.catalogue.like(escape_like(catalogue) + ".%", escape=_LIKE_ESCAPE),
    )


def _subject_catalogues(session: Session, key: str) -> tuple[str, ...]:
    rows = session.scalars(select(SubjectRow.catalogues).where(SubjectRow.term_key == key))
    seen: dict[str, None] = {}
    for catalogues in rows:
        for catalogue in catalogues:
            seen.setdefault(catalogue, None)
    return tuple(seen)


def search_items(session: Session, query: SearchQuery) -> SearchPage:
    conditions: list[ColumnElement[bool]] = []
    text_match: ColumnElement[bool] = false()
    subject_catalogues: tuple[str, ...] = ()

    if query.text and query.text.strip():
        key = search_key(query.text)
        # search_text is already normalized and lower-cased, so plain LIKE
        # is enough, and it can use the trigram index.
        text_match = ItemRow.search_text.like(f"%{escape_like(key)}%", escape=_LIKE_ESCAPE)
        subject_catalogues = _subject_catalogues(session, key)
        conditions.append(or_(text_match, *(_in_catalogue(c) for c in subject_catalogues)))

    if query.catalogue:
        conditions.append(_in_catalogue(query.catalogue.strip().lower()))

    total = session.scalar(select(func.count()).select_from(ItemRow).where(*conditions)) or 0
    items = session.scalars(
        select(ItemRow)
        .where(*conditions)
        .order_by(
            case((text_match, 0), else_=1),
            ItemRow.source,
            ItemRow.source_row,
        )
        .limit(query.limit)
        .offset(query.offset)
    ).all()
    return SearchPage(total=total, items=list(items), subject_catalogues=subject_catalogues)


def find_by_id(session: Session, catalogue: str, number: str) -> list[ItemRow]:
    """All items with this ID. More than one means a duplicate in the source."""
    item_id = f"{catalogue.strip().lower()}/{number.strip().lower()}"
    return list(
        session.scalars(
            select(ItemRow).where(ItemRow.item_id == item_id).order_by(ItemRow.source_row)
        )
    )


def issue_counts(session: Session) -> dict[str, int]:
    """Number of data-quality issues of each kind, most common first."""
    rows = session.execute(
        select(IssueRow.kind, func.count()).group_by(IssueRow.kind).order_by(func.count().desc())
    )
    return {kind: count for kind, count in rows}
