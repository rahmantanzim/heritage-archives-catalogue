"""Database tables and connection helpers (SQLAlchemy 2.0).

Three tables:
- items:    one row per catalogue item (poster, book, ...)
- subjects: the Main List subject index, used to widen searches
- issues:   every data-quality problem found while reading

The tables are created by Alembic migrations (see `migrations/`), not by
this module. Keep both in step: a change here needs a new migration.
"""

from __future__ import annotations

from sqlalchemy import ARRAY, Index, Integer, String, Text, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class ItemRow(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Not unique: the source has duplicate IDs, and we keep every copy.
    item_id: Mapped[str] = mapped_column(String(80), index=True)
    catalogue: Mapped[str] = mapped_column(String(30), index=True)
    number: Mapped[str] = mapped_column(String(40))
    id_original: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    title_original: Mapped[str] = mapped_column(Text)
    subject: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    fixes: Mapped[list[str]] = mapped_column(ARRAY(String(30)))
    source: Mapped[str] = mapped_column(String(100))
    source_row: Mapped[int] = mapped_column(Integer)
    # Lower-cased, Unicode-normalized text of all searchable fields.
    search_text: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        Index(
            "ix_items_search_text_trgm",
            "search_text",
            postgresql_using="gin",
            postgresql_ops={"search_text": "gin_trgm_ops"},
        ),
    )


class SubjectRow(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(Text)
    term_key: Mapped[str] = mapped_column(Text, index=True)  # normalized term
    reference: Mapped[str] = mapped_column(Text)
    catalogues: Mapped[list[str]] = mapped_column(ARRAY(String(30)))
    source: Mapped[str] = mapped_column(String(100))
    source_row: Mapped[int] = mapped_column(Integer)


class IssueRow(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    detail: Mapped[str] = mapped_column(Text)
    value: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(100))
    source_row: Mapped[int] = mapped_column(Integer)


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)
