from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.entity_type import EntityType
from ai_news_digest.domain.enums.relationship_activity_status import (
    RelationshipActivityStatus,
)
from ai_news_digest.domain.enums.relationship_status import RelationshipStatus
from ai_news_digest.domain.enums.relationship_type import RelationshipType


class ProvenanceSource(StrEnum):
    """Source from which a relationship was derived."""

    DETERMINISTIC = "deterministic"
    AI_EXTRACTED = "ai_extracted"
    MANUAL = "manual"


@dataclass(slots=True)
class Relationship:
    """
    Represents a directed relationship between two entities in the knowledge graph.

    Provenance is mandatory: every relationship must trace back to an
    article, story cluster, claim, or evidence.
    """

    id: UUID
    subject_entity_type: EntityType
    subject_entity_id: UUID
    relationship_type: RelationshipType
    object_entity_type: EntityType
    object_entity_id: UUID
    status: RelationshipStatus
    confidence: float | None = None
    provenance_source: ProvenanceSource = ProvenanceSource.DETERMINISTIC
    article_id: UUID | None = None
    story_cluster_id: UUID | None = None
    claim_id: UUID | None = None
    evidence_id: UUID | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_prompt_version: str | None = None
    schema_version: str = "v1"
    processing_metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    observed_at: datetime | None = None
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    observation_count: int = 1
    source_count: int = 1
    activity_score: float = 0.0
    activity_status: RelationshipActivityStatus = RelationshipActivityStatus.STABLE

    @staticmethod
    def create(
        *,
        subject_entity_type: EntityType,
        subject_entity_id: UUID,
        relationship_type: RelationshipType,
        object_entity_type: EntityType,
        object_entity_id: UUID,
        status: RelationshipStatus = RelationshipStatus.CANDIDATE,
        confidence: float | None = None,
        provenance_source: ProvenanceSource = ProvenanceSource.DETERMINISTIC,
        article_id: UUID | None = None,
        story_cluster_id: UUID | None = None,
        claim_id: UUID | None = None,
        evidence_id: UUID | None = None,
        ai_provider: str | None = None,
        ai_model: str | None = None,
        ai_prompt_version: str | None = None,
        schema_version: str = "v1",
        processing_metadata: dict[str, str] | None = None,
        observed_at: datetime | None = None,
        first_observed_at: datetime | None = None,
        last_observed_at: datetime | None = None,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        observation_count: int = 1,
        source_count: int = 1,
        activity_score: float = 0.0,
        activity_status: RelationshipActivityStatus = RelationshipActivityStatus.STABLE,
    ) -> Relationship:
        """Factory method for creating a new relationship."""
        now = datetime.now(UTC)
        return Relationship(
            id=uuid4(),
            subject_entity_type=subject_entity_type,
            subject_entity_id=subject_entity_id,
            relationship_type=relationship_type,
            object_entity_type=object_entity_type,
            object_entity_id=object_entity_id,
            status=status,
            confidence=confidence,
            provenance_source=provenance_source,
            article_id=article_id,
            story_cluster_id=story_cluster_id,
            claim_id=claim_id,
            evidence_id=evidence_id,
            ai_provider=ai_provider,
            ai_model=ai_model,
            ai_prompt_version=ai_prompt_version,
            schema_version=schema_version,
            processing_metadata=processing_metadata or {},
            created_at=now,
            updated_at=now,
            observed_at=observed_at or now,
            first_observed_at=first_observed_at or now,
            last_observed_at=last_observed_at or now,
            valid_from=valid_from,
            valid_to=valid_to,
            observation_count=observation_count,
            source_count=source_count,
            activity_score=activity_score,
            activity_status=activity_status,
        )

    def update_status(self, status: RelationshipStatus) -> None:
        """Update the relationship status (e.g., to VERIFIED, DISPUTED)."""
        self.status = status
        self.updated_at = datetime.now(UTC)

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(UTC)

    def record_observation(
        self,
        *,
        observed_at: datetime,
        source_id: UUID | None = None,
    ) -> None:
        """Record a new observation of this relationship.

        Updates last_observed_at and increments observation_count.
        Does NOT create a new canonical relationship row.
        """
        self.last_observed_at = observed_at
        self.observation_count += 1
        if source_id is not None:
            self.source_count += 1
        if self.first_observed_at is None:
            self.first_observed_at = observed_at
        self.updated_at = datetime.now(UTC)


__all__ = ["ProvenanceSource", "Relationship"]
