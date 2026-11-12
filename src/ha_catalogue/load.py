"""Load the cleaned catalogue into PostgreSQL.

Run:  python -m ha_catalogue.load data/raw

Each run replaces everything, inside one transaction. If anything fails,
the database keeps the previous load, so it is never half-loaded.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from ha_catalogue.db import IssueRow, ItemRow, SubjectRow, make_engine, make_session_factory
from ha_catalogue.ingest import read_all
from ha_catalogue.models import CatalogueItem, Issue, ReadResult, SubjectEntry
from ha_catalogue.settings import get_settings
from ha_catalogue.text import search_key

logger = logging.getLogger(__name__)


def _item_values(item: CatalogueItem) -> dict[str, object]:
    searchable = (item.item_id, item.title, item.subject, item.publisher, item.notes)
    return {
        "item_id": item.item_id,
        "catalogue": item.catalogue,
        "number": item.number,
        "id_original": item.id_original,
        "title": item.title,
        "title_original": item.title_original,
        "subject": item.subject,
        "publisher": item.publisher,
        "notes": item.notes,
        "fixes": [str(fix) for fix in item.fixes],
        "source": item.source,
        "source_row": item.row,
        "search_text": search_key(" ".join(part for part in searchable if part)),
    }


def _subject_values(entry: SubjectEntry) -> dict[str, object]:
    return {
        "term": entry.term,
        "term_key": search_key(entry.term),
        "reference": entry.reference,
        "catalogues": list(entry.catalogues),
        "source": entry.source,
        "source_row": entry.row,
    }


def _issue_values(issue: Issue) -> dict[str, object]:
    return {
        "kind": str(issue.kind),
        "detail": issue.detail,
        "value": issue.value,
        "source": issue.source,
        "source_row": issue.row,
    }


def replace_all(session: Session, result: ReadResult) -> None:
    """Replace the tables' contents with `result`. The caller commits."""
    for table in (ItemRow, SubjectRow, IssueRow):
        session.execute(delete(table))
    if result.items:
        session.execute(insert(ItemRow), [_item_values(i) for i in result.items])
    if result.subjects:
        session.execute(insert(SubjectRow), [_subject_values(s) for s in result.subjects])
    if result.issues:
        session.execute(insert(IssueRow), [_issue_values(i) for i in result.issues])


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raw_dir = Path(argv[1]) if len(argv) > 1 else Path("data/raw")

    result = read_all(raw_dir)
    engine = make_engine(get_settings().database_url)
    session_factory = make_session_factory(engine)
    with session_factory.begin() as session:
        replace_all(session, result)

    logger.info(
        "Loaded %d items, %d subject entries, %d issues",
        len(result.items),
        len(result.subjects),
        len(result.issues),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
