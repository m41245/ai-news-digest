"""Add M93 intelligence evaluation tables.

Revision ID: 031
Revises: 030
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(128), nullable=False),
        sa.Column("evaluation_type", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dataset_version", sa.String(64), nullable=False, server_default="production"),
        sa.Column("benchmark_version", sa.String(64), nullable=False, server_default="m93-v1"),
        sa.Column("configuration_version", sa.String(64), nullable=False, server_default="v1"),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(32), nullable=True),
        sa.Column("schema_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metric_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evaluation_runs_run_id", "evaluation_runs", ["run_id"], unique=True)
    op.create_index("ix_evaluation_runs_status", "evaluation_runs", ["status"])
    op.create_index("ix_evaluation_runs_evaluation_type", "evaluation_runs", ["evaluation_type"])
    op.create_index("ix_evaluation_runs_scope", "evaluation_runs", ["scope"])
    op.create_index("ix_evaluation_runs_provider", "evaluation_runs", ["provider"])
    op.create_index("ix_evaluation_runs_started_at", "evaluation_runs", ["started_at"])

    op.create_table(
        "evaluation_metrics",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("metric_type", sa.String(64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scope", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(32), nullable=True),
        sa.Column("schema_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("dataset_version", sa.String(64), nullable=False, server_default="production"),
        sa.Column("benchmark_version", sa.String(64), nullable=False, server_default="m93-v1"),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evaluation_metrics_run_id", "evaluation_metrics", ["run_id"])
    op.create_index("ix_evaluation_metrics_metric_type", "evaluation_metrics", ["metric_type"])
    op.create_index("ix_evaluation_metrics_scope", "evaluation_metrics", ["scope"])
    op.create_index("ix_evaluation_metrics_provider", "evaluation_metrics", ["provider"])

    op.create_table(
        "quality_snapshots",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("snapshot_id", sa.String(128), nullable=False),
        sa.Column("evaluation_run_id", sa.String(36), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.String(128), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("dataset_version", sa.String(64), nullable=False, server_default="production"),
        sa.Column("benchmark_version", sa.String(64), nullable=False, server_default="m93-v1"),
        sa.Column("configuration_version", sa.String(64), nullable=False, server_default="v1"),
        sa.Column("overall_quality", sa.Float(), nullable=True),
        sa.Column("structured_output_validity", sa.Float(), nullable=True),
        sa.Column("summary_presence", sa.Float(), nullable=True),
        sa.Column("provenance_completeness", sa.Float(), nullable=True),
        sa.Column("evidence_attachment_rate", sa.Float(), nullable=True),
        sa.Column("extraction_success_rate", sa.Float(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quality_snapshots_snapshot_id", "quality_snapshots", ["snapshot_id"], unique=True)
    op.create_index("ix_quality_snapshots_evaluated_at", "quality_snapshots", ["evaluated_at"])
    op.create_index("ix_quality_snapshots_scope", "quality_snapshots", ["scope"])


def downgrade() -> None:
    op.drop_index("ix_quality_snapshots_scope", table_name="quality_snapshots")
    op.drop_index("ix_quality_snapshots_evaluated_at", table_name="quality_snapshots")
    op.drop_index("ix_quality_snapshots_snapshot_id", table_name="quality_snapshots")
    op.drop_table("quality_snapshots")
    op.drop_index("ix_evaluation_metrics_provider", table_name="evaluation_metrics")
    op.drop_index("ix_evaluation_metrics_scope", table_name="evaluation_metrics")
    op.drop_index("ix_evaluation_metrics_metric_type", table_name="evaluation_metrics")
    op.drop_index("ix_evaluation_metrics_run_id", table_name="evaluation_metrics")
    op.drop_table("evaluation_metrics")
    op.drop_index("ix_evaluation_runs_started_at", table_name="evaluation_runs")
    op.drop_index("ix_evaluation_runs_provider", table_name="evaluation_runs")
    op.drop_index("ix_evaluation_runs_scope", table_name="evaluation_runs")
    op.drop_index("ix_evaluation_runs_evaluation_type", table_name="evaluation_runs")
    op.drop_index("ix_evaluation_runs_status", table_name="evaluation_runs")
    op.drop_index("ix_evaluation_runs_run_id", table_name="evaluation_runs")
    op.drop_table("evaluation_runs")
