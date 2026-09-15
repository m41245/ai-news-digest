"""Add user source follow and mute junction tables.

Revision ID: 027
Revises: 026
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "027"
down_revision: str | None = "026"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "user_followed_sources",
        sa.Column("id", sa.String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4())),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("source_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "source_id", name="uq_user_followed_source"),
    )

    op.create_table(
        "user_muted_sources",
        sa.Column("id", sa.String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4())),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("source_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "source_id", name="uq_user_muted_source"),
    )

    op.create_index(
        "ix_user_followed_sources_user_id_source_id",
        "user_followed_sources",
        ["user_id", "source_id"],
    )

    op.create_index(
        "ix_user_muted_sources_user_id_source_id",
        "user_muted_sources",
        ["user_id", "source_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_muted_sources_user_id_source_id", table_name="user_muted_sources")
    op.drop_index("ix_user_followed_sources_user_id_source_id", table_name="user_followed_sources")
    op.drop_table("user_muted_sources")
    op.drop_table("user_followed_sources")
