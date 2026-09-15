"""Add related entity ID columns to trends for personalization.

Revision ID: 028
Revises: 027
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "028"
down_revision: str | None = "027"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "trends",
        sa.Column("related_company_ids", sa.String(255), nullable=True),
    )
    op.add_column(
        "trends",
        sa.Column("related_topic_ids", sa.String(255), nullable=True),
    )
    op.add_column(
        "trends",
        sa.Column("related_category_ids", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("trends", "related_category_ids")
    op.drop_column("trends", "related_topic_ids")
    op.drop_column("trends", "related_company_ids")
