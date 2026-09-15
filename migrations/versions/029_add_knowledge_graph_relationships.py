"""Add knowledge graph relationships table.

Revision ID: 029
Revises: 028
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "029"
down_revision: str | None = "028"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "relationships",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("subject_entity_type", sa.String(16), nullable=False, index=True),
        sa.Column("subject_entity_id", sa.String(36), nullable=False, index=True),
        sa.Column("relationship_type", sa.String(32), nullable=False, index=True),
        sa.Column("object_entity_type", sa.String(16), nullable=False, index=True),
        sa.Column("object_entity_id", sa.String(36), nullable=False, index=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="candidate",
            index=True,
        ),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column(
            "provenance_source",
            sa.String(32),
            nullable=False,
            server_default="deterministic",
            index=True,
        ),
        sa.Column("article_id", sa.String(36), nullable=True, index=True),
        sa.Column("story_cluster_id", sa.String(36), nullable=True, index=True),
        sa.Column("claim_id", sa.String(36), nullable=True, index=True),
        sa.Column("evidence_id", sa.String(36), nullable=True, index=True),
        sa.Column("ai_provider", sa.String(64), nullable=True),
        sa.Column("ai_model", sa.String(128), nullable=True),
        sa.Column("ai_prompt_version", sa.String(32), nullable=True),
        sa.Column("schema_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("processing_metadata", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default="now()",
            nullable=False,
            index=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default="now()",
            nullable=False,
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.UniqueConstraint(
            "subject_entity_type",
            "subject_entity_id",
            "relationship_type",
            "object_entity_type",
            "object_entity_id",
            name="uq_relationship_canonical",
        ),
        sa.Index(
            "ix_relationships_subject_lookup",
            "subject_entity_type",
            "subject_entity_id",
            "status",
        ),
        sa.Index(
            "ix_relationships_object_lookup",
            "object_entity_type",
            "object_entity_id",
            "status",
        ),
        sa.Index(
            "ix_relationships_provenance",
            "provenance_source",
            "article_id",
            "story_cluster_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("relationships")
