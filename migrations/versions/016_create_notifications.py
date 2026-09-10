"""Create notification tables.

Revision ID: 016
Revises: 015
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: str | None = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="info"),
        sa.Column("story_id", sa.String(length=36), nullable=True),
        sa.Column("article_id", sa.String(length=36), nullable=True),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("topic_id", sa.String(length=36), nullable=True),
        sa.Column("digest_id", sa.String(length=36), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("deduplication_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["story_id"], ["story_clusters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["digest_id"], ["digests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_story_id", "notifications", ["story_id"])
    op.create_index("ix_notifications_article_id", "notifications", ["article_id"])
    op.create_index("ix_notifications_company_id", "notifications", ["company_id"])
    op.create_index("ix_notifications_topic_id", "notifications", ["topic_id"])
    op.create_index("ix_notifications_digest_id", "notifications", ["digest_id"])
    op.create_index("ix_notifications_dedup_key", "notifications", ["deduplication_key"], unique=True)
    op.create_index("ix_notifications_expires_at", "notifications", ["expires_at"])

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("notification_id", sa.String(length=36), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_deliveries_notification_id", "notification_deliveries", ["notification_id"])

    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("immediate_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("daily_digest_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("weekly_digest_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("min_importance", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("min_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("notify_followed_companies", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notify_followed_topics", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notify_corrections", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notify_story_evolution", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("quiet_hours_start", sa.String(length=5), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=5), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=False, server_default="UTC"),
        sa.Column("max_per_day", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("unsubscribe_token", sa.String(length=255), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_notification_preferences_unsubscribe_token", "notification_preferences", ["unsubscribe_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_notification_preferences_unsubscribe_token", table_name="notification_preferences")
    op.drop_table("notification_preferences")
    op.drop_index("ix_notification_deliveries_notification_id", table_name="notification_deliveries")
    op.drop_table("notification_deliveries")
    op.drop_index("ix_notifications_expires_at", table_name="notifications")
    op.drop_index("ix_notifications_dedup_key", table_name="notifications")
    op.drop_index("ix_notifications_digest_id", table_name="notifications")
    op.drop_index("ix_notifications_topic_id", table_name="notifications")
    op.drop_index("ix_notifications_company_id", table_name="notifications")
    op.drop_index("ix_notifications_article_id", table_name="notifications")
    op.drop_index("ix_notifications_story_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
