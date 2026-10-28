"""Add source trust decision audit records.

Revision ID: 034
Revises: 033
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_trust_decisions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("actor_user_id", sa.String(36), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("previous_status", sa.String(32), nullable=False),
        sa.Column("resulting_status", sa.String(32), nullable=False),
        sa.Column("previous_is_active", sa.Boolean(), nullable=False),
        sa.Column("resulting_is_active", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("validation_outcome", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_source_trust_decisions_source_id", "source_trust_decisions", ["source_id"])
    op.create_index(
        "ix_source_trust_decisions_actor_user_id", "source_trust_decisions", ["actor_user_id"]
    )
    op.create_index(
        "ix_source_trust_decisions_created_at", "source_trust_decisions", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_source_trust_decisions_created_at", table_name="source_trust_decisions")
    op.drop_index("ix_source_trust_decisions_actor_user_id", table_name="source_trust_decisions")
    op.drop_index("ix_source_trust_decisions_source_id", table_name="source_trust_decisions")
    op.drop_table("source_trust_decisions")
