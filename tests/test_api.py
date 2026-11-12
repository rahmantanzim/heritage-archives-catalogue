"""API and database tests.

They need a disposable PostgreSQL database whose name ends in "_test":

    TEST_DATABASE_URL=postgresql+psycopg://ha:PASSWORD@127.0.0.1:5432/ha_catalogue_test pytest

Without TEST_DATABASE_URL they are skipped. They drop and recreate every
table in that database through the real Alembic migrations.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

from ha_catalogue.api import MAX_PAGE_SIZE, create_app
from ha_catalogue.cleaning import Fix
from ha_catalogue.db import make_engine, make_session_factory
from ha_catalogue.load import replace_all
from ha_catalogue.models import CatalogueItem, Issue, IssueKind, ReadResult, SubjectEntry

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
PROJECT_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set")


def _item(catalogue: str, number: str, title: str, row: int, **extra) -> CatalogueItem:
    return CatalogueItem(
        source="test.csv",
        row=row,
        catalogue=catalogue,
        number=number,
        id_original=f"{catalogue} ({number})",
        title=title,
        title_original=extra.pop("title_original", title),
        **extra,
    )


SAMPLE = ReadResult(
    items=[
        _item(
            "256",
            "222",
            "Ist Art exhibition",
            2,
            title_original="ওংঃ অৎঃ বীযরনরঃরড়হ",
            publisher="Rajshahi University",
            fixes=(Fix.ENGLISH_RECOVERED,),
        ),
        _item("256", "13", "কেন আওয়ামী লীগ কে চাই না", 3),
        _item("256", "13", "দেশের গানের কনসার্ট", 4, publisher="চ্যানেল আই"),
        _item("189.22", "1", "আসাদুজ্জামান আসাদ, যশোর জেলার ইতিহাস", 5, subject="Jessore"),
        # Stored with ড + nukta (two characters) instead of ড় (one).
        _item("189.13", "7", "বাংলাদেশের প্রাচীন মস\u09a1\u09bcক", 6, subject="Dhaka"),
        _item("189.130", "1", "Not a sub-catalogue of 189.13", 7),
        _item("256", "500", "100% Literacy campaign", 8),
    ],
    subjects=[
        SubjectEntry("main.csv", 2, "Posters", "256", ("256",)),
        SubjectEntry("main.csv", 3, "Local History", "189", ("189",)),
    ],
    issues=[
        Issue("test.csv", 4, IssueKind.DUPLICATE_ID, "256/13 also used on row 3", "13"),
        Issue("test.csv", 2, IssueKind.ENGLISH_RECOVERED, "recovered", "ওংঃ অৎঃ বীযরনরঃরড়হ"),
        Issue("test.csv", 9, IssueKind.ENGLISH_RECOVERED, "recovered", "ঘবংঃষব"),
    ],
)


@pytest.fixture(scope="module")
def session_factory():
    assert TEST_DATABASE_URL is not None
    database = make_url(TEST_DATABASE_URL).database or ""
    if not database.endswith("_test"):
        pytest.fail(f"refusing to reset {database!r}: its name must end in '_test'")

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = make_engine(TEST_DATABASE_URL)
    factory = make_session_factory(engine)
    with factory.begin() as session:
        replace_all(session, SAMPLE)
    yield factory
    engine.dispose()


@pytest.fixture(scope="module")
def client(session_factory) -> Iterator[TestClient]:
    with TestClient(create_app(session_factory)) as test_client:
        yield test_client


def _ids(response) -> list[str]:
    return [item["item_id"] for item in response.json()["items"]]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_english_is_case_insensitive(client):
    response = client.get("/items", params={"q": "rajshahi UNIVERSITY"})
    assert response.status_code == 200
    assert _ids(response) == ["256/222"]
    item = response.json()["items"][0]
    assert item["fixes"] == ["english_recovered"]
    assert item["title_original"] == "ওংঃ অৎঃ বীযরনরঃরড়হ"


def test_search_bengali(client):
    assert _ids(client.get("/items", params={"q": "যশোর"})) == ["189.22/1"]


def test_search_matches_either_form_of_the_same_letter(client):
    # Query with ড় as one character; the stored text uses ড + nukta.
    assert _ids(client.get("/items", params={"q": "মস\u09dcক"})) == ["189.13/7"]


def test_subject_index_widens_search(client):
    response = client.get("/items", params={"q": "posters"})
    body = response.json()
    assert body["subject_catalogues"] == ["256"]
    assert body["total"] == 4  # every item in catalogue 256


def test_subject_catalogue_includes_sub_catalogues(client):
    body = client.get("/items", params={"q": "local history"}).json()
    assert body["total"] == 3  # 189.22, 189.13 and 189.130


def test_catalogue_filter_does_not_match_longer_numbers(client):
    # 189.13 must not include 189.130.
    assert _ids(client.get("/items", params={"catalogue": "189.13"})) == ["189.13/7"]


def test_percent_sign_is_matched_literally(client):
    assert _ids(client.get("/items", params={"q": "100%"})) == ["256/500"]
    assert client.get("/items", params={"q": "%"}).json()["total"] == 1


def test_pagination(client):
    first = client.get("/items", params={"catalogue": "256", "limit": 2}).json()
    second = client.get("/items", params={"catalogue": "256", "limit": 2, "offset": 2}).json()
    assert first["total"] == second["total"] == 4
    seen = [i["item_id"] for i in first["items"] + second["items"]]
    assert len(seen) == 4
    assert sorted(seen) == sorted(["256/222", "256/13", "256/13", "256/500"])


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": MAX_PAGE_SIZE + 1}, {"offset": -1}, {"q": "x" * 201}],
)
def test_rejects_bad_parameters(client, params):
    assert client.get("/items", params=params).status_code == 422


def test_get_item_returns_every_duplicate(client):
    response = client.get("/items/256/13")
    assert response.status_code == 200
    assert [item["source_row"] for item in response.json()] == [3, 4]


def test_get_item_is_case_insensitive(client):
    assert client.get("/items/189.13/7").status_code == 200


def test_get_missing_item(client):
    assert client.get("/items/999/1").status_code == 404


def test_issue_summary(client):
    assert client.get("/issues/summary").json() == {"english_recovered": 2, "duplicate_id": 1}


def test_load_replaces_previous_data(session_factory, client):
    smaller = ReadResult(items=[SAMPLE.items[0]])
    with session_factory.begin() as session:
        replace_all(session, smaller)
    try:
        assert client.get("/items").json()["total"] == 1
        assert client.get("/issues/summary").json() == {}
    finally:
        with session_factory.begin() as session:
            replace_all(session, SAMPLE)
