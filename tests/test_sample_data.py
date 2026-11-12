"""The committed sample (data/sample/) must load and show every feature.

This is what a visitor runs, so it must never silently break or lose the
examples that make the demo worth running.
"""

from pathlib import Path

import pytest

from ha_catalogue.cleaning import Fix
from ha_catalogue.ingest import SOURCES, read_all
from ha_catalogue.models import IssueKind, ReadResult

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"


@pytest.fixture(scope="module")
def sample() -> ReadResult:
    return read_all(SAMPLE_DIR)


def test_sample_has_every_source_file():
    assert sorted(path.name for path in SAMPLE_DIR.glob("*.csv")) == sorted(SOURCES)


def test_sample_loads_items_from_every_file(sample):
    assert len(sample.items) > 1000
    assert {item.source for item in sample.items} == set(SOURCES) - {"catalogue-000-main-list.csv"}
    assert len(sample.subjects) > 700  # the whole subject index, for search


def test_sample_shows_every_cleaning_fix(sample):
    fixes = {fix for item in sample.items for fix in item.fixes}
    assert fixes == {Fix.BIJOY_CONVERTED, Fix.ENGLISH_RECOVERED}


@pytest.mark.parametrize(
    "kind",
    [
        IssueKind.DUPLICATE_ID,
        IssueKind.MALFORMED_ID,
        IssueKind.CONTINUATION_ROW,
        IssueKind.RESERVED_RANGE,
        IssueKind.SPLIT_ROW_REPAIRED,
    ],
)
def test_sample_shows_each_kind_of_problem(sample, kind):
    assert any(issue.kind is kind for issue in sample.issues)
