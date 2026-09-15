"""Add story_activity table for M83 breaking and developing story detection.

Revision ID: 024
Revises: 023
Create Date: 2026-09-15 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "024"
down_revision: str | None = "023"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "story_activity",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("story_cluster_id", sa.String(36), nullable=False, index=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="stale",
            index=True,
        ),
        sa.Column("activity_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("detection_version", sa.String(32), nullable=False, index=True),
        sa.Column("article_count_recent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_source_count_recent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recent_article_velocity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("latest_article_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_article_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recent_claim_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recent_conflict_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("state_change_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_story_activity_cluster_status",
        "story_activity",
        ["story_cluster_id", "status"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_story_activity_detection_version", table_name="story_activity")
    op.drop_index("ix_story_activity_evaluated_at", table_name="story_activity")
    op.drop_index("ix_story_activity_status", table_name="story_activity")
    op.drop_index("ix_story_activity_story_cluster_id", table_name="story_activity")
    op.drop_index("ix_story_activity_cluster_status", table_name="story_activity")
    op.drop_table("story_activity")


__all__ = ["revision", "down_revision"]
