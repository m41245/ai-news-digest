"""Align topics.name length with ORM and project conventions.

Revision ID: 035
Revises: 034
Create Date: 2026-10-29

Upgrade widens ``topics.name`` from ``VARCHAR(64)`` to ``VARCHAR(255)`` so
that topic names can use the same length as company names and other
free-form labels.

Downgrade restores ``VARCHAR(64)``. This can fail when one or more
existing ``topics.name`` values are longer than 64 characters: the
database refuses to narrow the column and does not silently truncate or
delete data. The explicit precondition below makes that failure occur
before the column alteration, with a clear error, instead of relying on
the database's type-conversion error. No data is truncated or deleted by
this migration in either direction.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "035"
down_revision: str | None = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Widen topics.name from 64 to 255 characters."""
    op.alter_column(
        "topics",
        "name",
        existing_type=sa.String(64),
        type_=sa.String(255),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Restore topics.name to 64 characters.

    Fails before altering the column if any topic name exceeds 64
    characters, so the database never has to truncate or drop data.
    """
    bind = op.get_bind()
    over_limit = bind.execute(
        sa.text("SELECT COUNT(*) FROM topics WHERE length(name) > 64")
    ).scalar_one()
    if over_limit:
        raise RuntimeError(
            "Cannot downgrade topics.name to VARCHAR(64): "
            f"{over_limit} topic name(s) exceed 64 characters. "
            "Shorten or remove those names before downgrading."
        )
    op.alter_column(
        "topics",
        "name",
        existing_type=sa.String(255),
        type_=sa.String(64),
        existing_nullable=False,
    )
