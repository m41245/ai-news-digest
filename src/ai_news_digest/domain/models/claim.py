from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.claim_status import ClaimStatus
from ai_news_digest.domain.enums.claim_type import ClaimType


@dataclass(slots=True)
class Claim:
    """
    Represents a factual claim extracted from an article by AI analysis.

    Claims are explicitly distinguished from AI interpretation.
    A claim without verified evidence is marked UNVERIFIED.
    """

    id: UUID
    article_id: UUID
    source_id: UUID
    claim_text: str
    claim_type: ClaimType = ClaimType.OTHER
    confidence: float | None = None
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    evidence_support_score: float | None = None
    schema_version: str = "v1"
    prompt_version: str | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    processing_metadata: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def create(
        *,
        article_id: UUID,
        source_id: UUID,
        claim_text: str,
        claim_type: ClaimType = ClaimType.OTHER,
        confidence: float | None = None,
        schema_version: str = "v1",
        prompt_version: str | None = None,
        ai_provider: str | None = None,
        ai_model: str | None = None,
        processing_metadata: dict[str, str] | None = None,
    ) -> Claim:
        """Factory method for creating a new claim."""
        return Claim(
            id=uuid4(),
            article_id=article_id,
            source_id=source_id,
            claim_text=claim_text,
            claim_type=claim_type,
            confidence=confidence,
            schema_version=schema_version,
            prompt_version=prompt_version,
            ai_provider=ai_provider,
            ai_model=ai_model,
            processing_metadata=processing_metadata or {},
        )

    def update_status(
        self,
        status: ClaimStatus,
        evidence_support_score: float | None = None,
    ) -> None:
        """Update the claim status after evidence validation."""
        self.status = status
        if evidence_support_score is not None:
            self.evidence_support_score = max(0.0, min(1.0, evidence_support_score))
