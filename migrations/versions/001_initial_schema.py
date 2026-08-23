"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create sources table
    op.create_table(
        "sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("feed_url", sa.String(2048), nullable=False),
        sa.Column("website_url", sa.String(2048), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("feed_url"),
    )
    op.create_index("ix_sources_name", "sources", ["name"], unique=True)
    op.create_index("ix_sources_feed_url", "sources", ["feed_url"], unique=True)

    # Create categories table
    op.create_table(
        "categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_categories_name", "categories", ["name"], unique=True)

    # Create articles table
    article_status_enum = sa.Enum(
        "new",
        "fetched",
        "summarized",
        "categorized",
        "published",
        "failed",
        name="articlestatus",
        native_enum=True,
        validate_strings=True,
    )

    op.create_table(
        "articles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("category_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("status", article_status_enum, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("url"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_articles_source_id", "articles", ["source_id"])
    op.create_index("ix_articles_category_id", "articles", ["category_id"])
    op.create_index("ix_articles_status", "articles", ["status"])
    op.create_index("ix_articles_published_at", "articles", ["published_at"])
    op.create_index("ix_articles_url", "articles", ["url"], unique=True)

    # Create digests table
    digest_format_enum = sa.Enum(
        "html",
        "markdown",
        "pdf",
        name="digestformat",
        native_enum=False,
        validate_strings=True,
    )
    digest_format_enum.create(op.get_bind())

    op.create_table(
        "digests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("format", digest_format_enum, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_digests_format", "digests", ["format"])
    op.create_index("ix_digests_generated_at", "digests", ["generated_at"])

    # Create digest_articles association table
    op.create_table(
        "digest_articles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("digest_id", sa.String(36), nullable=False),
        sa.Column("article_id", sa.String(36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("digest_id", "article_id", name="uq_digest_article"),
        sa.ForeignKeyConstraint(["digest_id"], ["digests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_digest_articles_digest_id", "digest_articles", ["digest_id"])
    op.create_index("ix_digest_articles_article_id", "digest_articles", ["article_id"])


def downgrade() -> None:
    op.drop_index("ix_digest_articles_article_id", table_name="digest_articles")
    op.drop_index("ix_digest_articles_digest_id", table_name="digest_articles")
    op.drop_table("digest_articles")

    op.drop_index("ix_digests_generated_at", table_name="digests")
    op.drop_index("ix_digests_format", table_name="digests")
    op.drop_table("digests")

    digest_format_enum = sa.Enum(
        "html",
        "markdown",
        "pdf",
        name="digestformat",
        native_enum=False,
        validate_strings=True,
    )
    digest_format_enum.drop(op.get_bind())

    op.drop_index("ix_articles_url", table_name="articles")
    op.drop_index("ix_articles_published_at", table_name="articles")
    op.drop_index("ix_articles_status", table_name="articles")
    op.drop_index("ix_articles_category_id", table_name="articles")
    op.drop_index("ix_articles_source_id", table_name="articles")
    op.drop_table("articles")

    article_status_enum = sa.Enum(
        "new",
        "fetched",
        "summarized",
        "categorized",
        "published",
        "failed",
        name="articlestatus",
        native_enum=False,
        validate_strings=True,
    )
    article_status_enum.drop(op.get_bind())

    op.drop_index("ix_categories_name", table_name="categories")
    op.drop_table("categories")

    op.drop_index("ix_sources_feed_url", table_name="sources")
    op.drop_index("ix_sources_name", table_name="sources")
    op.drop_table("sources")
