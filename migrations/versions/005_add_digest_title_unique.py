"""Add unique constraint on digest title

Revision ID: 005
Revises: 004
Create Date: 2026-08-20 22:30:00.000000
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add unique constraint on digest title."""
    op.create_unique_constraint("uq_digests_title", "digests", ["title"])


def downgrade() -> None:
    """Remove unique constraint on digest title."""
    op.drop_constraint("uq_digests_title", "digests", type_="unique")
