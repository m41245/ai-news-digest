"""Add notification scheduling columns.

Revision ID: 017
Revises: 016
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "017"
down_revision: str | None = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_notifications_scheduled_for",
        "notifications",
        ["scheduled_for"],
    )

    op.add_column(
        "notification_deliveries",
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification_deliveries",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification_deliveries",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification_deliveries",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_notification_deliveries_next_attempt_at",
        "notification_deliveries",
        ["next_attempt_at"],
    )

    op.add_column(
        "notification_deliveries",
        sa.Column("provider_idempotency_key", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_notification_deliveries_provider_idempotency_key",
        "notification_deliveries",
        ["provider_idempotency_key"],
    )

    op.add_column(
        "notification_deliveries",
        sa.Column("delivery_window", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "notification_deliveries",
        sa.Column("suppression_reason", sa.String(length=100), nullable=True),
    )

    op.create_index(
        "ix_notification_deliveries_status_next_attempt_at",
        "notification_deliveries",
        ["status", "next_attempt_at"],
    )
    op.create_index(
        "ix_notification_deliveries_status_scheduled_for",
        "notification_deliveries",
        ["status", "scheduled_for"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_deliveries_status_scheduled_for", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_status_next_attempt_at", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_provider_idempotency_key", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_next_attempt_at", table_name="notification_deliveries")
    op.drop_column("notification_deliveries", "suppression_reason")
    op.drop_column("notification_deliveries", "delivery_window")
    op.drop_column("notification_deliveries", "provider_idempotency_key")
    op.drop_column("notification_deliveries", "next_attempt_at")
    op.drop_column("notification_deliveries", "processing_started_at")
    op.drop_column("notification_deliveries", "claimed_at")
    op.drop_column("notification_deliveries", "scheduled_for")

    op.drop_index("ix_notifications_scheduled_for", table_name="notifications")
    op.drop_column("notifications", "scheduled_for")
