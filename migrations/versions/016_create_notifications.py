"""Create notification tables.

Revision ID: 016
Revises: 015
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "016"
down_revision: str | None = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        op.Column("id", sa.String(length=36), nullable=False),
        op.Column("user_id", sa.String(length=36), nullable=False),
        op.Column("notification_type", sa.String(length=50), nullable=False),
        op.Column("title", sa.String(length=500), nullable=False),
        op.Column("body", sa.Text(), nullable=False),
        op.Column("severity", sa.String(length=20), nullable=False, server_default="info"),
        op.Column("story_id", sa.String(length=36), nullable=True),
        op.Column("article_id", sa.String(length=36), nullable=True),
        op.Column("company_id", sa.String(length=36), nullable=True),
        op.Column("topic_id", sa.String(length=36), nullable=True),
        op.Column("digest_id", sa.String(length=36), nullable=True),
        op.Column("extra_data", sa.JSON(), nullable=True),
        op.Column("deduplication_key", sa.String(length=255), nullable=False),
        op.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        op.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        op.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        op.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        op.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        op.ForeignKeyConstraint(["story_id"], ["story_clusters.id"], ondelete="SET NULL"),
        op.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="SET NULL"),
        op.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        op.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        op.ForeignKeyConstraint(["digest_id"], ["digests.id"], ondelete="SET NULL"),
        op.PrimaryKeyConstraint("id"),
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
        op.Column("id", sa.String(length=36), nullable=False),
        op.Column("notification_id", sa.String(length=36), nullable=False),
        op.Column("channel", sa.String(length=20), nullable=False),
        op.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        op.Column("provider_message_id", sa.String(length=255), nullable=True),
        op.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        op.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        op.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        op.Column("failure_reason", sa.Text(), nullable=True),
        op.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        op.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        op.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        op.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_deliveries_notification_id", "notification_deliveries", ["notification_id"])

    op.create_table(
        "notification_preferences",
        op.Column("user_id", sa.String(length=36), nullable=False),
        op.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        op.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        op.Column("immediate_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        op.Column("daily_digest_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        op.Column("weekly_digest_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        op.Column("min_importance", sa.Float(), nullable=False, server_default="0.0"),
        op.Column("min_confidence", sa.Float(), nullable=False, server_default="0.0"),
        op.Column("notify_followed_companies", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        op.Column("notify_followed_topics", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        op.Column("notify_corrections", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        op.Column("notify_story_evolution", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        op.Column("quiet_hours_start", sa.String(length=5), nullable=True),
        op.Column("quiet_hours_end", sa.String(length=5), nullable=True),
        op.Column("timezone", sa.String(length=50), nullable=False, server_default="UTC"),
        op.Column("max_per_day", sa.Integer(), nullable=False, server_default="10"),
        op.Column("unsubscribe_token", sa.String(length=255), nullable=True, unique=True),
        op.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        op.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        op.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        op.PrimaryKeyConstraint("user_id"),
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
