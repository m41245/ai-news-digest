from __future__ import annotations

import json
from uuid import UUID

from ai_news_digest.domain.enums.claim_status import ClaimStatus
from ai_news_digest.domain.enums.claim_type import ClaimType
from ai_news_digest.domain.models.claim import Claim
from ai_news_digest.infrastructure.database.models.claim_model import (
    ClaimModel,
)


class ClaimMapper:
    """
    Maps between Claim domain objects and ClaimModel ORM entities.
    """

    @staticmethod
    def to_model(claim: Claim) -> ClaimModel:
        """Convert a domain Claim into a new ORM ClaimModel."""
        return ClaimModel(
            id=str(claim.id),
            article_id=str(claim.article_id),
            source_id=str(claim.source_id),
            claim_text=claim.claim_text,
            claim_type=claim.claim_type.value,
            confidence=claim.confidence,
            status=claim.status.value,
            evidence_support_score=claim.evidence_support_score,
            schema_version=claim.schema_version,
            prompt_version=claim.prompt_version,
            ai_provider=claim.ai_provider,
            ai_model=claim.ai_model,
            processing_metadata=json.dumps(claim.processing_metadata, ensure_ascii=False)
            if claim.processing_metadata
            else None,
        )

    @staticmethod
    def update_model(model: ClaimModel, claim: Claim) -> None:
        """Update an existing ORM model from a domain Claim."""
        model.claim_text = claim.claim_text
        model.claim_type = claim.claim_type.value
        model.confidence = claim.confidence
        model.status = claim.status.value
        model.evidence_support_score = claim.evidence_support_score
        model.schema_version = claim.schema_version
        model.prompt_version = claim.prompt_version
        model.ai_provider = claim.ai_provider
        model.ai_model = claim.ai_model
        model.processing_metadata = (
            json.dumps(claim.processing_metadata, ensure_ascii=False)
            if claim.processing_metadata
            else None
        )

    @staticmethod
    def to_domain(model: ClaimModel) -> Claim:
        """Convert an ORM ClaimModel into a domain Claim."""
        try:
            claim_type = ClaimType(model.claim_type)
        except ValueError:
            claim_type = ClaimType.OTHER

        try:
            claim_status = ClaimStatus(model.status)
        except ValueError:
            claim_status = ClaimStatus.UNVERIFIED

        processing_metadata: dict[str, str] = {}
        if model.processing_metadata:
            try:
                parsed = json.loads(model.processing_metadata)
                if isinstance(parsed, dict):
                    processing_metadata = {str(k): str(v) for k, v in parsed.items()}
            except (ValueError, TypeError):
                pass

        return Claim(
            id=UUID(model.id),
            article_id=UUID(model.article_id),
            source_id=UUID(model.source_id),
            claim_text=model.claim_text,
            claim_type=claim_type,
            confidence=model.confidence,
            status=claim_status,
            evidence_support_score=model.evidence_support_score,
            schema_version=model.schema_version,
            prompt_version=model.prompt_version,
            ai_provider=model.ai_provider,
            ai_model=model.ai_model,
            processing_metadata=processing_metadata,
            created_at=model.created_at,
        )


__all__ = ["ClaimMapper"]
