"""Add temporal graph intelligence fields to relationships table.

Revision ID: 030
Revises: 029
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "030"
down_revision: str | None = "029"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "relationships",
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "relationships",
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "relationships",
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "relationships",
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "relationships",
        sa.Column("observation_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "relationships",
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "relationships",
        sa.Column("activity_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "relationships",
        sa.Column("activity_status", sa.String(32), nullable=False, server_default="stable"),
    )
    op.create_index(
        "ix_relationships_temporal",
        "relationships",
        ["subject_entity_type", "subject_entity_id", "last_observed_at"],
    )
    op.create_index(
        "ix_relationships_activity",
        "relationships",
        ["activity_status", "last_observed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_relationships_activity", table_name="relationships")
    op.drop_index("ix_relationships_temporal", table_name="relationships")
    op.drop_column("relationships", "activity_status")
    op.drop_column("relationships", "activity_score")
    op.drop_column("relationships", "source_count")
    op.drop_column("relationships", "observation_count")
    op.drop_column("relationships", "valid_to")
    op.drop_column("relationships", "valid_from")
    op.drop_column("relationships", "last_observed_at")
    op.drop_column("relationships", "first_observed_at")
