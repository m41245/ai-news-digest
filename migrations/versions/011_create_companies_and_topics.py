"""Create companies, topics, and many-to-many associations.

Revision ID: 011
Revises: 010
Create Date: 2026-09-04 05:10:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create companies, topics, and association tables; backfill associations."""
    op.create_table(
        "companies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("aliases_json", sa.Text(), nullable=True),
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
    op.create_index("ix_companies_slug", "companies", ["slug"], unique=True)
    op.create_index("ix_companies_name", "companies", ["name"], unique=True)

    op.create_table(
        "topics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
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
    op.create_index("ix_topics_slug", "topics", ["slug"], unique=True)
    op.create_index("ix_topics_name", "topics", ["name"], unique=True)

    op.create_table(
        "article_companies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("article_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["article_id"], ["articles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "article_id", "company_id", name="uq_article_companies"
        ),
    )
    op.create_index(
        "ix_article_companies_article_id", "article_companies", ["article_id"]
    )
    op.create_index(
        "ix_article_companies_company_id", "article_companies", ["company_id"]
    )

    op.create_table(
        "article_topics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("article_id", sa.String(36), nullable=False),
        sa.Column("topic_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["article_id"], ["articles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("article_id", "topic_id", name="uq_article_topics"),
    )
    op.create_index(
        "ix_article_topics_article_id", "article_topics", ["article_id"]
    )
    op.create_index("ix_article_topics_topic_id", "article_topics", ["topic_id"])

    op.create_table(
        "article_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("article_id", sa.String(36), nullable=False),
        sa.Column("category_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["article_id"], ["articles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "article_id", "category_id", name="uq_article_categories"
        ),
    )
    op.create_index(
        "ix_article_categories_article_id", "article_categories", ["article_id"]
    )
    op.create_index(
        "ix_article_categories_category_id", "article_categories", ["category_id"]
    )

    # Backfill: replicate existing Article.category_id into the new
    # many-to-many table so nothing is lost.
    op.execute(
        "INSERT INTO article_categories (id, article_id, category_id, created_at) "
        "SELECT gen_random_uuid()::text, id, category_id, now() "
        "FROM articles WHERE category_id IS NOT NULL"
    )


def downgrade() -> None:
    """Drop the new tables in reverse order."""
    op.drop_index(
        "ix_article_categories_category_id", table_name="article_categories"
    )
    op.drop_index(
        "ix_article_categories_article_id", table_name="article_categories"
    )
    op.drop_table("article_categories")

    op.drop_index("ix_article_topics_topic_id", table_name="article_topics")
    op.drop_index("ix_article_topics_article_id", table_name="article_topics")
    op.drop_table("article_topics")

    op.drop_index(
        "ix_article_companies_company_id", table_name="article_companies"
    )
    op.drop_index(
        "ix_article_companies_article_id", table_name="article_companies"
    )
    op.drop_table("article_companies")

    op.drop_index("ix_topics_name", table_name="topics")
    op.drop_index("ix_topics_slug", table_name="topics")
    op.drop_table("topics")

    op.drop_index("ix_companies_name", table_name="companies")
    op.drop_index("ix_companies_slug", table_name="companies")
    op.drop_table("companies")
