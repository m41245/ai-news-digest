"""Add structured AI intelligence fields to articles.

Revision ID: 010
Revises: 009
Create Date: 2026-09-04 05:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add structured-intelligence columns to ``articles``."""
    op.add_column("articles", sa.Column("importance_score", sa.Float(), nullable=True))
    op.add_column("articles", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("articles", sa.Column("ai_provider", sa.String(64), nullable=True))
    op.add_column("articles", sa.Column("ai_model", sa.String(128), nullable=True))
    op.add_column(
        "articles",
        sa.Column("ai_processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("articles", sa.Column("key_takeaways_json", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("why_it_matters", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("topics_json", sa.Text(), nullable=True))


def downgrade() -> None:
    """Drop structured-intelligence columns from ``articles``."""
    op.drop_column("articles", "topics_json")
    op.drop_column("articles", "why_it_matters")
    op.drop_column("articles", "key_takeaways_json")
    op.drop_column("articles", "ai_processed_at")
    op.drop_column("articles", "ai_model")
    op.drop_column("articles", "ai_provider")
    op.drop_column("articles", "confidence")
    op.drop_column("articles", "importance_score")
