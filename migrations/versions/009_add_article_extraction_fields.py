"""Add article extraction pipeline metadata.

Revision ID: 009
Revises: 008
Create Date: 2026-09-04 02:45:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add extraction-pipeline columns to ``articles``."""
    op.add_column(
        "articles",
        sa.Column(
            "extraction_method",
            sa.String(32),
            nullable=False,
            server_default="rss",
        ),
    )
    op.add_column(
        "articles",
        sa.Column(
            "extraction_quality",
            sa.String(16),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column(
        "articles",
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("content_char_count", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_articles_extraction_method",
        "articles",
        ["extraction_method"],
    )


def downgrade() -> None:
    """Drop extraction-pipeline columns from ``articles``."""
    op.drop_index("ix_articles_extraction_method", table_name="articles")
    op.drop_column("articles", "content_char_count")
    op.drop_column("articles", "extracted_at")
    op.drop_column("articles", "extraction_quality")
    op.drop_column("articles", "extraction_method")
