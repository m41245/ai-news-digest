from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ai_news_digest.domain.enums.entity_type import EntityType
from ai_news_digest.domain.enums.relationship_status import RelationshipStatus
from ai_news_digest.domain.enums.relationship_type import RelationshipType
from ai_news_digest.infrastructure.database.base import Base


class RelationshipModel(Base):
    """
    Database representation of a knowledge graph relationship.

    Relationships reference existing canonical entities (companies, topics,
    stories, articles) without duplicating them. Provenance is mandatory.
    """

    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    subject_entity_type: Mapped[EntityType] = mapped_column(
        String(16),
        nullable=False,
        index=True,
    )
    subject_entity_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    relationship_type: Mapped[RelationshipType] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    object_entity_type: Mapped[EntityType] = mapped_column(
        String(16),
        nullable=False,
        index=True,
    )
    object_entity_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    status: Mapped[RelationshipStatus] = mapped_column(
        String(32),
        nullable=False,
        server_default=RelationshipStatus.CANDIDATE.value,
        index=True,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    provenance_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="deterministic",
        index=True,
    )

    article_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    story_cluster_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    claim_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    evidence_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    ai_provider: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    ai_model: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    ai_prompt_version: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    schema_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="v1",
    )

    processing_metadata: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        onupdate="now()",
        nullable=False,
    )
    observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "subject_entity_type",
            "subject_entity_id",
            "relationship_type",
            "object_entity_type",
            "object_entity_id",
            name="uq_relationship_canonical",
        ),
        Index(
            "ix_relationships_subject_lookup",
            "subject_entity_type",
            "subject_entity_id",
            "status",
        ),
        Index(
            "ix_relationships_object_lookup",
            "object_entity_type",
            "object_entity_id",
            "status",
        ),
        Index(
            "ix_relationships_provenance",
            "provenance_source",
            "article_id",
            "story_cluster_id",
        ),
    )
