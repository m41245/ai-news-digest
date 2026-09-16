"""Add M96 saved intelligence, user collections, and story following.

Revision ID: 033
Revises: 032
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_collections",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_user_collection_name"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_collections_user_id", "user_collections", ["user_id"])

    op.create_table(
        "saved_stories",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("story_cluster_id", sa.String(36), nullable=False),
        sa.Column("collection_id", sa.String(36), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "story_cluster_id", name="uq_user_saved_story"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["story_cluster_id"], ["story_clusters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["collection_id"], ["user_collections.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_saved_stories_user_id", "saved_stories", ["user_id"])
    op.create_index("ix_saved_stories_story_cluster_id", "saved_stories", ["story_cluster_id"])
    op.create_index("ix_saved_stories_collection_id", "saved_stories", ["collection_id"])
    op.create_index("ix_saved_stories_created_at", "saved_stories", ["created_at"])

    op.create_table(
        "followed_stories",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("story_cluster_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "story_cluster_id", name="uq_user_followed_story"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["story_cluster_id"], ["story_clusters.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_followed_stories_user_id", "followed_stories", ["user_id"])
    op.create_index("ix_followed_stories_story_cluster_id", "followed_stories", ["story_cluster_id"])
    op.create_index("ix_followed_stories_created_at", "followed_stories", ["created_at"])


def downgrade() -> None:
    op.drop_table("followed_stories")
    op.drop_table("saved_stories")
    op.drop_table("user_collections")
