"""Add intelligent digest editorial fields.

Revision ID: 020
Revises: 019
Create Date: 2026-09-13 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "020"
down_revision: str | None = "019"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "digests",
        sa.Column("top_story_cluster_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "digests",
        sa.Column("stories", sa.Text(), nullable=True),
    )
    op.add_column(
        "digests",
        sa.Column("generation_metadata", sa.Text(), nullable=True),
    )
    op.add_column(
        "digests",
        sa.Column("generation_method", sa.String(32), nullable=True),
    )
    op.add_column(
        "digests",
        sa.Column("provider", sa.String(64), nullable=True),
    )
    op.add_column(
        "digests",
        sa.Column("model", sa.String(128), nullable=True),
    )
    op.create_index(
        "ix_digests_top_story_cluster_id",
        "digests",
        ["top_story_cluster_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_digests_top_story_cluster_id", table_name="digests")
    op.drop_column("digests", "model")
    op.drop_column("digests", "provider")
    op.drop_column("digests", "generation_method")
    op.drop_column("digests", "generation_metadata")
    op.drop_column("digests", "stories")
    op.drop_column("digests", "top_story_cluster_id")


__all__ = ["revision", "down_revision"]
