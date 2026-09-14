"""Add claims and claim_evidence tables for M81.

Revision ID: 022
Revises: 021
Create Date: 2026-09-15 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "022"
down_revision: str | None = "021"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "claims",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("article_id", sa.String(36), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(32), nullable=False, server_default="other"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="unverified"),
        sa.Column("evidence_support_score", sa.Float(), nullable=True),
        sa.Column("schema_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("prompt_version", sa.String(32), nullable=True),
        sa.Column("ai_provider", sa.String(64), nullable=True),
        sa.Column("ai_model", sa.String(128), nullable=True),
        sa.Column("processing_metadata", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_claims_article_id", "claims", ["article_id"], unique=False)
    op.create_index("ix_claims_source_id", "claims", ["source_id"], unique=False)
    op.create_index("ix_claims_status", "claims", ["status"], unique=False)
    op.create_index("ix_claims_created_at", "claims", ["created_at"], unique=False)

    op.create_table(
        "claim_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("claim_id", sa.String(36), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("article_id", sa.String(36), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_type", sa.String(32), nullable=False, server_default="article_text"),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("source_location", sa.String(256), nullable=True),
        sa.Column("anchor_sentence_index", sa.Integer(), nullable=True),
        sa.Column("anchor_paragraph_index", sa.Integer(), nullable=True),
        sa.Column("anchor_character_start", sa.Integer(), nullable=True),
        sa.Column("anchor_character_end", sa.Integer(), nullable=True),
        sa.Column("anchor_content_hash", sa.String(64), nullable=True),
        sa.Column("strength", sa.String(32), nullable=False, server_default="moderate"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_claim_evidence_claim_id", "claim_evidence", ["claim_id"], unique=False)
    op.create_index("ix_claim_evidence_article_id", "claim_evidence", ["article_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_claim_evidence_article_id", table_name="claim_evidence")
    op.drop_index("ix_claim_evidence_claim_id", table_name="claim_evidence")
    op.drop_table("claim_evidence")

    op.drop_index("ix_claims_created_at", table_name="claims")
    op.drop_index("ix_claims_status", table_name="claims")
    op.drop_index("ix_claims_source_id", table_name="claims")
    op.drop_index("ix_claims_article_id", table_name="claims")
    op.drop_table("claims")


__all__ = ["revision", "down_revision"]
