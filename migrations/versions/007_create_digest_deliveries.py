"""Create digest_deliveries table

Revision ID: 007
Revises: 006
Create Date: 2026-08-22 23:50:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create the digest_deliveries table."""
    op.create_table(
        "digest_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("digest_id", sa.String(36), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text, nullable=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "digest_id",
            "recipient",
            name="uq_digest_deliveries_digest_recipient",
        ),
    )
    op.create_index(
        "ix_digest_deliveries_digest_id",
        "digest_deliveries",
        ["digest_id"],
    )
    op.create_index(
        "ix_digest_deliveries_status",
        "digest_deliveries",
        ["status"],
    )


def downgrade() -> None:
    """Drop the digest_deliveries table."""
    op.drop_index("ix_digest_deliveries_status", table_name="digest_deliveries")
    op.drop_index("ix_digest_deliveries_digest_id", table_name="digest_deliveries")
    op.drop_constraint(
        "uq_digest_deliveries_digest_recipient",
        "digest_deliveries",
        type_="unique",
    )
    op.drop_table("digest_deliveries")
