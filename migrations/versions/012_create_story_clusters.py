"""Create story_clusters table and add cluster_id to articles.

Revision ID: 012
Revises: 011
Create Date: 2026-09-04 12:30:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create story_clusters table and add cluster_id to articles."""
    op.create_table(
        "story_clusters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "first_published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("representative_article_id", sa.String(36), nullable=True),
        sa.Column("importance_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_story_clusters_slug", "story_clusters", ["slug"], unique=True)
    op.create_index("ix_story_clusters_status", "story_clusters", ["status"])
    op.create_index(
        "ix_story_clusters_first_published_at", "story_clusters", ["first_published_at"]
    )

    op.add_column(
        "articles",
        sa.Column("cluster_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_articles_cluster_id", "articles", ["cluster_id"])
    op.create_foreign_key(
        "fk_articles_cluster_id",
        "articles",
        "story_clusters",
        ["cluster_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Drop story_clusters table and remove cluster_id from articles."""
    op.drop_constraint("fk_articles_cluster_id", "articles", type_="foreignkey")
    op.drop_index("ix_articles_cluster_id", table_name="articles")
    op.drop_column("articles", "cluster_id")

    op.drop_index("ix_story_clusters_first_published_at", table_name="story_clusters")
    op.drop_index("ix_story_clusters_status", table_name="story_clusters")
    op.drop_index("ix_story_clusters_slug", table_name="story_clusters")
    op.drop_table("story_clusters")
