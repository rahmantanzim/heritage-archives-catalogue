"""Create items, subjects and issues tables.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pg_trgm lets PostgreSQL use an index for "contains" (ILIKE '%...%') search.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.String(40), nullable=False),
        sa.Column("catalogue", sa.String(30), nullable=False),
        sa.Column("number", sa.String(10), nullable=False),
        sa.Column("id_original", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("title_original", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("fixes", postgresql.ARRAY(sa.String(30)), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
    )
    op.create_index("ix_items_item_id", "items", ["item_id"])
    op.create_index("ix_items_catalogue", "items", ["catalogue"])
    op.create_index(
        "ix_items_search_text_trgm",
        "items",
        ["search_text"],
        postgresql_using="gin",
        postgresql_ops={"search_text": "gin_trgm_ops"},
    )

    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("term", sa.Text(), nullable=False),
        sa.Column("term_key", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=False),
        sa.Column("catalogues", postgresql.ARRAY(sa.String(30)), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
    )
    op.create_index("ix_subjects_term_key", "subjects", ["term_key"])

    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
    )
    op.create_index("ix_issues_kind", "issues", ["kind"])


def downgrade() -> None:
    op.drop_table("issues")
    op.drop_table("subjects")
    op.drop_table("items")
