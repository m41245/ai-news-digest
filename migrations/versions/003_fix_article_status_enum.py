"""Fix ArticleStatus enum drift

Revision ID: 003
Revises: 002
Create Date: 2026-08-20 00:00:00.000000

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add missing ArticleStatus values and remove unused 'published' value."""
    # Add new values
    op.execute("ALTER TYPE articlestatus ADD VALUE IF NOT EXISTS 'processed'")
    op.execute("ALTER TYPE articlestatus ADD VALUE IF NOT EXISTS 'ready'")

    # Note: PostgreSQL does not support dropping enum values directly.
    # If 'published' was never used in production, it can remain as dead weight.
    # If removal is required, it must be done via a multi-step migration:
    # 1. Create a new enum type
    # 2. Alter columns to use the new type
    # 3. Drop the old type
    # For now, we leave 'published' in place to avoid data migration risk.


def downgrade() -> None:
    """Revert enum changes."""
    # PostgreSQL cannot drop enum values, so downgrade is a no-op
    # for the values. A full downgrade would require type replacement.
    pass
