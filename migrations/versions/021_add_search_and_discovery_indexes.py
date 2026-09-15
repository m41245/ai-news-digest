"""Add search and discovery indexes for M72.

Revision ID: 021
Revises: 020
Create Date: 2026-09-14 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "021"
down_revision: str | None = "020"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_index(
        "ix_articles_importance_published",
        "articles",
        ["importance_score", "published_at"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_articles_importance_published", table_name="articles")


__all__ = ["revision", "down_revision"]
