"""Add is_admin column to users table

Revision ID: 004
Revises: 003
Create Date: 2026-08-20 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add is_admin column to users table."""
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Remove is_admin column from users table."""
    op.drop_column("users", "is_admin")
