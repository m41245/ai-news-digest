"""Add conflicts table for M82 cross-source contradiction detection.

Revision ID: 023
Revises: 022
Create Date: 2026-09-15 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "023"
down_revision: str | None = "022"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "conflicts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("claim_a_id", sa.String(36), nullable=False, index=True),
        sa.Column("claim_b_id", sa.String(36), nullable=False, index=True),
        sa.Column("article_a_id", sa.String(36), nullable=False, index=True),
        sa.Column("article_b_id", sa.String(36), nullable=False, index=True),
        sa.Column("source_a_id", sa.String(36), nullable=False, index=True),
        sa.Column("source_b_id", sa.String(36), nullable=False, index=True),
        sa.Column(
            "conflict_type",
            sa.String(32),
            nullable=False,
            server_default="other",
        ),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="potential",
            index=True,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("detection_version", sa.String(32), nullable=False, index=True),
        sa.Column("story_cluster_id", sa.String(36), nullable=True, index=True),
        sa.Column("same_source", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("conflict_metadata", sa.Text(), nullable=True),
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
        "ix_conflicts_created_at",
        "conflicts",
        ["created_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_conflicts_unique_pair",
        "conflicts",
        ["claim_a_id", "claim_b_id", "detection_version"],
        unique=True,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_conflicts_story_cluster_id", table_name="conflicts")
    op.drop_index("ix_conflicts_detection_version", table_name="conflicts")
    op.drop_index("ix_conflicts_status", table_name="conflicts")
    op.drop_index("ix_conflicts_source_b_id", table_name="conflicts")
    op.drop_index("ix_conflicts_source_a_id", table_name="conflicts")
    op.drop_index("ix_conflicts_article_b_id", table_name="conflicts")
    op.drop_index("ix_conflicts_article_a_id", table_name="conflicts")
    op.drop_index("ix_conflicts_claim_b_id", table_name="conflicts")
    op.drop_index("ix_conflicts_claim_a_id", table_name="conflicts")
    op.drop_index("ix_conflicts_unique_pair", table_name="conflicts")
    op.drop_index("ix_conflicts_created_at", table_name="conflicts")
    op.drop_table("conflicts")


__all__ = ["revision", "down_revision"]
