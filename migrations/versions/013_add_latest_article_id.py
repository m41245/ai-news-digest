"""Add latest_article_id to story_clusters.

Revision ID: 013
Revises: 012
Create Date: 2026-09-04 14:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add latest_article_id to story_clusters."""
    op.add_column(
        "story_clusters",
        sa.Column("latest_article_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_story_clusters_latest_article_id",
        "story_clusters",
        ["latest_article_id"],
    )


def downgrade() -> None:
    """Remove latest_article_id from story_clusters."""
    op.drop_index("ix_story_clusters_latest_article_id", table_name="story_clusters")
    op.drop_column("story_clusters", "latest_article_id")
