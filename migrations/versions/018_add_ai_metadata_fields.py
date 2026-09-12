"""Add AI metadata fields to articles.

Revision ID: 018
Revises: 017
Create Date: 2026-09-12 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add AI metadata columns to ``articles``."""
    op.add_column("articles", sa.Column("ai_input_tokens", sa.Integer(), nullable=True))
    op.add_column("articles", sa.Column("ai_output_tokens", sa.Integer(), nullable=True))
    op.add_column(
        "articles",
        sa.Column("ai_prompt_version", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    """Drop AI metadata columns from ``articles``."""
    op.drop_column("articles", "ai_prompt_version")
    op.drop_column("articles", "ai_output_tokens")
    op.drop_column("articles", "ai_input_tokens")


__all__ = ["revision", "down_revision"]
