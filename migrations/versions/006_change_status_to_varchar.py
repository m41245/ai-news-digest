"""Change articles.status from native enum to VARCHAR

Revision ID: 006
Revises: 005
Create Date: 2026-08-22 12:00:00.000000

"""

from __future__ import annotations

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Convert articles.status column from native PostgreSQL enum to VARCHAR."""
    op.execute("ALTER TABLE articles ALTER COLUMN status " "TYPE VARCHAR(20) USING status::text")
    op.execute("DROP TYPE IF EXISTS articlestatus")


def downgrade() -> None:
    """Revert articles.status column back to native PostgreSQL enum."""
    op.execute(
        "CREATE TYPE articlestatus AS ENUM ("
        "'new', 'fetched', 'summarized', 'categorized', "
        "'published', 'failed', 'processed', 'ready')"
    )
    op.execute(
        "ALTER TABLE articles ALTER COLUMN status " "TYPE articlestatus USING status::articlestatus"
    )
