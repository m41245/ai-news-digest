"""Add ranking fields to story_clusters.

Revision ID: 019
Revises: 018
Create Date: 2026-09-13 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "019"
down_revision: str | None = "018"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add ranking_score and ranking_explanation columns to story_clusters."""
    op.add_column("story_clusters", sa.Column("ranking_score", sa.Float(), nullable=True))
    op.add_column(
        "story_clusters",
        sa.Column("ranking_explanation", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop ranking columns from story_clusters."""
    op.drop_column("story_clusters", "ranking_explanation")
    op.drop_column("story_clusters", "ranking_score")


__all__ = ["revision", "down_revision"]
