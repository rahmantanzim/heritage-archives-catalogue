"""HTTP API for searching the catalogue (FastAPI).

Run:  uvicorn ha_catalogue.api:create_app --factory --reload
Docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from ha_catalogue.db import make_engine, make_session_factory
from ha_catalogue.search import SearchQuery, find_by_id, issue_counts, search_items
from ha_catalogue.settings import get_settings

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20
MAX_QUERY_LENGTH = 200


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: str
    catalogue: str
    number: str
    title: str
    subject: str | None
    publisher: str | None
    notes: str | None
    fixes: list[str]
    title_original: str
    id_original: str
    source: str
    source_row: int


class SearchOut(BaseModel):
    total: int
    limit: int
    offset: int
    subject_catalogues: list[str]
    items: list[ItemOut]


class HealthOut(BaseModel):
    status: str


def get_session(request: Request) -> Iterator[Session]:
    """One database session per request, closed when the request ends."""
    session_factory: sessionmaker = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def create_app(session_factory: sessionmaker | None = None) -> FastAPI:
    """Build the app. Tests pass their own session factory."""
    if session_factory is None:
        session_factory = make_session_factory(make_engine(get_settings().database_url))

    app = FastAPI(
        title="Heritage Archives Catalogue",
        description="Search the cleaned catalogue of Heritage Archives Bangladesh.",
        version="0.1.0",
    )

    app.state.session_factory = session_factory

    @app.get("/health")
    def health(session: SessionDep) -> HealthOut:
        session.execute(text("SELECT 1"))
        return HealthOut(status="ok")

    @app.get("/items")
    def search(
        session: SessionDep,
        q: Annotated[str | None, Query(max_length=MAX_QUERY_LENGTH)] = None,
        catalogue: Annotated[str | None, Query(max_length=30)] = None,
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> SearchOut:
        page = search_items(
            session, SearchQuery(text=q, catalogue=catalogue, limit=limit, offset=offset)
        )
        return SearchOut(
            total=page.total,
            limit=limit,
            offset=offset,
            subject_catalogues=list(page.subject_catalogues),
            items=[ItemOut.model_validate(item) for item in page.items],
        )

    @app.get("/items/{catalogue}/{number}")
    def get_item(session: SessionDep, catalogue: str, number: str) -> list[ItemOut]:
        items = find_by_id(session, catalogue, number)
        if not items:
            raise HTTPException(status_code=404, detail=f"No item {catalogue}/{number}")
        return [ItemOut.model_validate(item) for item in items]

    @app.get("/issues/summary")
    def issues_summary(session: SessionDep) -> dict[str, int]:
        return issue_counts(session)

    return app
