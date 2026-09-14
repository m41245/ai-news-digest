"""Add search and discovery indexes for M72.

Revision ID: 021
Revises: 020
Create Date: 2026-09-14 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "021"
down_revision: str | None = "020"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_index(
        "ix_articles_importance_score",
        "articles",
        ["importance_score"],
        unique=False,
    )
    op.create_index(
        "ix_articles_importance_published",
        "articles",
        ["importance_score", "published_at"],
        unique=False,
    )
    op.create_index(
        "ix_article_companies_company_id",
        "article_companies",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        "ix_article_topics_topic_id",
        "article_topics",
        ["topic_id"],
        unique=False,
    )
    op.create_index(
        "ix_story_clusters_status",
        "story_clusters",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_story_clusters_importance_score",
        "story_clusters",
        ["importance_score"],
        unique=False,
    )
    op.create_index(
        "ix_story_clusters_first_published_at",
        "story_clusters",
        ["first_published_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_story_clusters_first_published_at", table_name="story_clusters")
    op.drop_index("ix_story_clusters_importance_score", table_name="story_clusters")
    op.drop_index("ix_story_clusters_status", table_name="story_clusters")
    op.drop_index("ix_article_topics_topic_id", table_name="article_topics")
    op.drop_index("ix_article_companies_company_id", table_name="article_companies")
    op.drop_index("ix_articles_importance_published", table_name="articles")
    op.drop_index("ix_articles_importance_score", table_name="articles")


__all__ = ["revision", "down_revision"]
