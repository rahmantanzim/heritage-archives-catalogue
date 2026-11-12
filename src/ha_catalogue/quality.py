"""Checks that look across all items, not just one row."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from ha_catalogue.models import CatalogueItem, Issue, IssueKind


def find_duplicate_ids(items: Iterable[CatalogueItem]) -> list[Issue]:
    """One issue per extra copy of an ID. Both copies are kept as items."""
    by_id: dict[str, list[CatalogueItem]] = defaultdict(list)
    for item in items:
        by_id[item.item_id].append(item)

    issues: list[Issue] = []
    for item_id, copies in by_id.items():
        if len(copies) < 2:
            continue
        first = copies[0]
        for extra in copies[1:]:
            issues.append(
                Issue(
                    extra.source,
                    extra.row,
                    IssueKind.DUPLICATE_ID,
                    f"{item_id} also used on row {first.row}",
                    extra.id_original.strip(),
                )
            )
    return issues
