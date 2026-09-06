"""Add source trust-model fields.

Revision ID: 008
Revises: 007
Create Date: 2026-09-03 16:30:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add trust-model columns to ``sources``."""
    op.add_column(
        "sources",
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="pending_review",
        ),
    )
    op.add_column(
        "sources",
        sa.Column(
            "source_type",
            sa.String(32),
            nullable=False,
            server_default="other",
        ),
    )
    op.add_column(
        "sources",
        sa.Column("publisher", sa.String(255), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("verification_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "sources",
        sa.Column("last_successful_fetch_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("last_failed_fetch_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_sources_status", "sources", ["status"])
    op.create_index("ix_sources_source_type", "sources", ["source_type"])
    op.create_index("ix_sources_priority", "sources", ["priority"])

    # Backfill: existing sources that are active become ``verified`` so the new
    # digest gate does not silently empty today's digest. Inactive sources stay
    # ``pending_review`` and must be reviewed before they contribute again.
    op.execute(
        "UPDATE sources SET status = 'verified' WHERE is_active = true"
    )


def downgrade() -> None:
    """Drop trust-model columns from ``sources``."""
    op.drop_index("ix_sources_priority", table_name="sources")
    op.drop_index("ix_sources_source_type", table_name="sources")
    op.drop_index("ix_sources_status", table_name="sources")
    op.drop_column("sources", "failure_count")
    op.drop_column("sources", "last_failed_fetch_at")
    op.drop_column("sources", "last_successful_fetch_at")
    op.drop_column("sources", "priority")
    op.drop_column("sources", "verification_notes")
    op.drop_column("sources", "publisher")
    op.drop_column("sources", "source_type")
    op.drop_column("sources", "status")
