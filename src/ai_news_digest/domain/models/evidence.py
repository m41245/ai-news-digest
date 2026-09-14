from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.evidence_strength import EvidenceStrength
from ai_news_digest.domain.enums.evidence_type import EvidenceType


@dataclass(slots=True)
class EvidenceAnchor:
    """Location reference within source article content."""

    sentence_index: int | None = None
    paragraph_index: int | None = None
    character_start: int | None = None
    character_end: int | None = None
    content_hash: str | None = None


@dataclass(slots=True)
class Evidence:
    """
    Represents source material supporting a claim.

    Evidence references the actual source article without
    reproducing full copyrighted content.
    """

    id: UUID
    claim_id: UUID
    article_id: UUID
    evidence_type: EvidenceType = EvidenceType.ARTICLE_TEXT
    excerpt: str | None = None
    source_location: str | None = None
    anchor: EvidenceAnchor | None = None
    strength: EvidenceStrength = EvidenceStrength.MODERATE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        *,
        claim_id: UUID,
        article_id: UUID,
        evidence_type: EvidenceType = EvidenceType.ARTICLE_TEXT,
        excerpt: str | None = None,
        source_location: str | None = None,
        anchor: EvidenceAnchor | None = None,
        strength: EvidenceStrength = EvidenceStrength.MODERATE,
    ) -> Evidence:
        """Factory method for creating evidence."""
        return Evidence(
            id=uuid4(),
            claim_id=claim_id,
            article_id=article_id,
            evidence_type=evidence_type,
            excerpt=excerpt,
            source_location=source_location,
            anchor=anchor,
            strength=strength,
        )

    def is_bounded(self) -> bool:
        """Return True if the evidence is bounded (excerpt length is safe)."""
        if self.excerpt is None:
            return True
        return len(self.excerpt) <= 500
