"""Add indexes for personalized feed queries.

Revision ID: 015
Revises: 014
"""
from __future__ import annotations

from alembic import op

revision: str = "015"
down_revision: str | None = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_articles_status_published_at",
        "articles",
        ["status", "published_at"],
    )
    op.create_index(
        "ix_articles_cluster_id_published_at",
        "articles",
        ["cluster_id", "published_at"],
    )
    op.create_index(
        "ix_articles_source_type",
        "sources",
        ["source_type"],
    )
    op.create_index(
        "ix_user_followed_companies_user_id_company_id",
        "user_followed_companies",
        ["user_id", "company_id"],
    )
    op.create_index(
        "ix_user_followed_topics_user_id_topic_id",
        "user_followed_topics",
        ["user_id", "topic_id"],
    )
    op.create_index(
        "ix_user_followed_categories_user_id_category_id",
        "user_followed_categories",
        ["user_id", "category_id"],
    )
    op.create_index(
        "ix_user_muted_companies_user_id_company_id",
        "user_muted_companies",
        ["user_id", "company_id"],
    )
    op.create_index(
        "ix_user_muted_topics_user_id_topic_id",
        "user_muted_topics",
        ["user_id", "topic_id"],
    )
    op.create_index(
        "ix_user_muted_categories_user_id_category_id",
        "user_muted_categories",
        ["user_id", "category_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_muted_categories_user_id_category_id", table_name="user_muted_categories")
    op.drop_index("ix_user_muted_topics_user_id_topic_id", table_name="user_muted_topics")
    op.drop_index("ix_user_muted_companies_user_id_company_id", table_name="user_muted_companies")
    op.drop_index("ix_user_followed_categories_user_id_category_id", table_name="user_followed_categories")
    op.drop_index("ix_user_followed_topics_user_id_topic_id", table_name="user_followed_topics")
    op.drop_index("ix_user_followed_companies_user_id_company_id", table_name="user_followed_companies")
    op.drop_index("ix_articles_source_type", table_name="sources")
    op.drop_index("ix_articles_cluster_id_published_at", table_name="articles")
    op.drop_index("ix_articles_status_published_at", table_name="articles")
