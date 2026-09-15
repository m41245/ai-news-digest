"""Add story_events tables for M84 story evolution timeline.

Revision ID: 025
Revises: 024
Create Date: 2026-09-15 00:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "025"
down_revision: str | None = "024"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "story_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("story_cluster_id", sa.String(36), nullable=False, index=True),
        sa.Column("event_type", sa.String(32), nullable=False, server_default="other"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0"),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("representative_article_id", sa.String(36), nullable=True),
        sa.Column("processing_metadata", sa.Text, nullable=True),
        sa.Column("schema_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("sequence", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_story_events_cluster",
        "story_events",
        ["story_cluster_id"],
        unique=False,
        if_not_exists=True,
    )
    op.create_table(
        "story_event_articles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("story_event_id", sa.String(36), nullable=False, index=True),
        sa.Column("article_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "story_event_claims",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("story_event_id", sa.String(36), nullable=False, index=True),
        sa.Column("claim_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("story_event_claims")
    op.drop_table("story_event_articles")
    op.drop_index("ix_story_events_cluster", table_name="story_events")
    op.drop_table("story_events")


__all__ = ["down_revision", "revision"]
