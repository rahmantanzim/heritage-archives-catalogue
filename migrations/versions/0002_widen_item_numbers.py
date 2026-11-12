"""Widen item numbers for volume names such as "91c (দ্বাদশ খণ্ড)".

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("items", "number", type_=sa.String(40), existing_nullable=False)
    op.alter_column("items", "item_id", type_=sa.String(80), existing_nullable=False)


def downgrade() -> None:
    # Fails if a longer value is stored; reload the data first.
    op.alter_column("items", "item_id", type_=sa.String(40), existing_nullable=False)
    op.alter_column("items", "number", type_=sa.String(10), existing_nullable=False)
