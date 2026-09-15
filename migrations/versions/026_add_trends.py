"""Add trends table for M85 trend detection and emerging story intelligence.

Revision ID: 026
Revises: 025
Create Date: 2026-09-15 00:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "026"
down_revision: str | None = "025"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "trends",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trend_type", sa.String(32), nullable=False),
        sa.Column("canonical_key", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="stale"),
        sa.Column("trend_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("momentum_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recent_activity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("baseline_activity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("source_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("story_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("event_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("explanation", sa.Text, nullable=False),
        sa.Column("trend_metadata", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_trends_status",
        "trends",
        ["status"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_trends_trend_score",
        "trends",
        ["trend_score"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_trends_last_detected_at",
        "trends",
        ["last_detected_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_trends_canonical_key",
        "trends",
        ["canonical_key"],
        unique=True,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_trends_canonical_key", table_name="trends")
    op.drop_index("ix_trends_last_detected_at", table_name="trends")
    op.drop_index("ix_trends_trend_score", table_name="trends")
    op.drop_index("ix_trends_status", table_name="trends")
    op.drop_table("trends")


__all__ = ["down_revision", "revision"]
