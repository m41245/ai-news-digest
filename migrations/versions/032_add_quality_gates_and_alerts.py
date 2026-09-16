"""Add M94 quality gates, operational alerts, and component health snapshots.

Revision ID: 032
Revises: 031
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quality_gate_results",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("gate_id", sa.String(64), nullable=False),
        sa.Column("component", sa.String(64), nullable=False),
        sa.Column("metric_type", sa.String(64), nullable=False),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("operator", sa.String(16), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("evaluation_run_id", sa.String(36), nullable=True),
        sa.Column("configuration_version", sa.String(64), nullable=False, server_default="v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quality_gate_results_gate_id", "quality_gate_results", ["gate_id"])
    op.create_index("ix_quality_gate_results_component", "quality_gate_results", ["component"])
    op.create_index("ix_quality_gate_results_metric_type", "quality_gate_results", ["metric_type"])
    op.create_index("ix_quality_gate_results_result", "quality_gate_results", ["result"])
    op.create_index("ix_quality_gate_results_evaluation_run_id", "quality_gate_results", ["evaluation_run_id"])
    op.create_index("ix_quality_gate_results_created_at", "quality_gate_results", ["created_at"])

    op.create_table(
        "operational_alerts",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("alert_id", sa.String(128), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("component", sa.String(64), nullable=False),
        sa.Column("gate_id", sa.String(64), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("resolved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deduplication_key", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operational_alerts_alert_id", "operational_alerts", ["alert_id"], unique=True)
    op.create_index("ix_operational_alerts_severity", "operational_alerts", ["severity"])
    op.create_index("ix_operational_alerts_component", "operational_alerts", ["component"])
    op.create_index("ix_operational_alerts_gate_id", "operational_alerts", ["gate_id"])
    op.create_index("ix_operational_alerts_resolved", "operational_alerts", ["resolved"])
    op.create_index("ix_operational_alerts_created_at", "operational_alerts", ["created_at"])
    op.create_index("ix_operational_alerts_dedup_key", "operational_alerts", ["deduplication_key"])

    op.create_table(
        "component_health_snapshots",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("snapshot_id", sa.String(128), nullable=False),
        sa.Column("component", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("metric_type", sa.String(64), nullable=True),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("drift_state", sa.String(32), nullable=True),
        sa.Column("evaluation_run_id", sa.String(36), nullable=True),
        sa.Column("configuration_version", sa.String(64), nullable=False, server_default="v1"),
        sa.Column("warnings", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_component_health_snapshots_snapshot_id", "component_health_snapshots", ["snapshot_id"], unique=True)
    op.create_index("ix_component_health_snapshots_component", "component_health_snapshots", ["component"])
    op.create_index("ix_component_health_snapshots_status", "component_health_snapshots", ["status"])
    op.create_index("ix_component_health_snapshots_created_at", "component_health_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_component_health_snapshots_created_at", table_name="component_health_snapshots")
    op.drop_index("ix_component_health_snapshots_status", table_name="component_health_snapshots")
    op.drop_index("ix_component_health_snapshots_component", table_name="component_health_snapshots")
    op.drop_index("ix_component_health_snapshots_snapshot_id", table_name="component_health_snapshots")
    op.drop_table("component_health_snapshots")

    op.drop_index("ix_operational_alerts_dedup_key", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_created_at", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_resolved", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_gate_id", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_component", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_severity", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_alert_id", table_name="operational_alerts")
    op.drop_table("operational_alerts")

    op.drop_index("ix_quality_gate_results_created_at", table_name="quality_gate_results")
    op.drop_index("ix_quality_gate_results_evaluation_run_id", table_name="quality_gate_results")
    op.drop_index("ix_quality_gate_results_result", table_name="quality_gate_results")
    op.drop_index("ix_quality_gate_results_metric_type", table_name="quality_gate_results")
    op.drop_index("ix_quality_gate_results_component", table_name="quality_gate_results")
    op.drop_index("ix_quality_gate_results_gate_id", table_name="quality_gate_results")
    op.drop_table("quality_gate_results")
