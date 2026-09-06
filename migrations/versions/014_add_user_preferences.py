"""Add user preference profile and follow/mute junction tables.

Revision ID: 014
Revises: 013
Create Date: 2026-09-05 04:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "user_preference_profiles",
        sa.Column("user_id", sa.String(36), primary_key=True),
        sa.Column("min_importance", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("min_confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("feed_sort", sa.String(32), nullable=False, server_default="published_at"),
        sa.Column("freshness_window_days", sa.Integer, nullable=True),
        sa.Column("preferred_source_types_json", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_preference_profiles_user_id", "user_preference_profiles", ["user_id"], unique=True)

    op.create_table(
        "user_followed_companies",
        sa.Column("id", sa.String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4())),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("company_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "company_id", name="uq_user_followed_company"),
    )

    op.create_table(
        "user_followed_topics",
        sa.Column("id", sa.String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4())),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("topic_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "topic_id", name="uq_user_followed_topic"),
    )

    op.create_table(
        "user_followed_categories",
        sa.Column("id", sa.String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4())),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("category_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "category_id", name="uq_user_followed_category"),
    )

    op.create_table(
        "user_muted_companies",
        sa.Column("id", sa.String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4())),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("company_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "company_id", name="uq_user_muted_company"),
    )

    op.create_table(
        "user_muted_topics",
        sa.Column("id", sa.String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4())),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("topic_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "topic_id", name="uq_user_muted_topic"),
    )

    op.create_table(
        "user_muted_categories",
        sa.Column("id", sa.String(36), primary_key=True, default=lambda: str(__import__("uuid").uuid4())),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("category_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "category_id", name="uq_user_muted_category"),
    )

    op.create_index(
        "ix_articles_published_at_status",
        "articles",
        ["published_at", "status"],
    )
    op.create_index(
        "ix_articles_importance_score",
        "articles",
        ["importance_score"],
    )
    op.create_index(
        "ix_articles_confidence",
        "articles",
        ["confidence"],
    )
    op.create_index(
        "ix_articles_source_id_published_at",
        "articles",
        ["source_id", "published_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_articles_source_id_published_at", table_name="articles")
    op.drop_index("ix_articles_confidence", table_name="articles")
    op.drop_index("ix_articles_importance_score", table_name="articles")
    op.drop_index("ix_articles_published_at_status", table_name="articles")
    op.drop_table("user_muted_categories")
    op.drop_table("user_muted_topics")
    op.drop_table("user_muted_companies")
    op.drop_table("user_followed_categories")
    op.drop_table("user_followed_topics")
    op.drop_table("user_followed_companies")
    op.drop_index("ix_user_preference_profiles_user_id", table_name="user_preference_profiles")
    op.drop_table("user_preference_profiles")
