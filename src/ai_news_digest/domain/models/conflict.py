from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.conflict_status import ConflictStatus
from ai_news_digest.domain.enums.conflict_type import ConflictType


@dataclass(slots=True)
class Conflict:
    """
    Represents a potential conflict between two claims from different sources.

    A Conflict does NOT assert that one source is correct and the other is wrong.
    It only records that two claims about the same subject appear to contradict
    each other, along with the evidence and provenance needed for later review.
    """

    id: UUID
    claim_a_id: UUID
    claim_b_id: UUID
    article_a_id: UUID
    article_b_id: UUID
    source_a_id: UUID
    source_b_id: UUID
    conflict_type: ConflictType
    status: ConflictStatus
    confidence: float
    explanation: str
    detection_version: str
    story_cluster_id: UUID | None = None
    same_source: bool = False
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        *,
        claim_a_id: UUID,
        claim_b_id: UUID,
        article_a_id: UUID,
        article_b_id: UUID,
        source_a_id: UUID,
        source_b_id: UUID,
        conflict_type: ConflictType,
        confidence: float,
        explanation: str,
        detection_version: str,
        story_cluster_id: UUID | None = None,
        same_source: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> Conflict:
        """Factory method for creating a new conflict record."""
        return Conflict(
            id=uuid4(),
            claim_a_id=claim_a_id,
            claim_b_id=claim_b_id,
            article_a_id=article_a_id,
            article_b_id=article_b_id,
            source_a_id=source_a_id,
            source_b_id=source_b_id,
            conflict_type=conflict_type,
            status=ConflictStatus.POTENTIAL,
            confidence=min(max(confidence, 0.0), 1.0),
            explanation=explanation,
            detection_version=detection_version,
            story_cluster_id=story_cluster_id,
            same_source=same_source,
            metadata=metadata or {},
        )

    def update_status(self, status: ConflictStatus) -> None:
        """Update the conflict status (e.g., to CONFIRMED, DISMISSED)."""
        self.status = status
        self.updated_at = datetime.now(UTC)

    def update_explanation(self, explanation: str) -> None:
        """Update the explanation for this conflict."""
        self.explanation = explanation
        self.updated_at = datetime.now(UTC)


__all__ = ["Conflict"]
