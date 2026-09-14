from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.enums.evidence_strength import EvidenceStrength
from ai_news_digest.domain.enums.evidence_type import EvidenceType
from ai_news_digest.domain.models.evidence import Evidence, EvidenceAnchor
from ai_news_digest.infrastructure.database.models.claim_evidence_model import (
    ClaimEvidenceModel,
)


class EvidenceMapper:
    """
    Maps between Evidence domain objects and ClaimEvidenceModel ORM entities.
    """

    @staticmethod
    def to_model(evidence: Evidence) -> ClaimEvidenceModel:
        """Convert a domain Evidence into a new ORM ClaimEvidenceModel."""
        anchor = evidence.anchor
        return ClaimEvidenceModel(
            id=str(evidence.id),
            claim_id=str(evidence.claim_id),
            article_id=str(evidence.article_id),
            evidence_type=evidence.evidence_type.value,
            excerpt=evidence.excerpt,
            source_location=evidence.source_location,
            anchor_sentence_index=anchor.sentence_index if anchor else None,
            anchor_paragraph_index=anchor.paragraph_index if anchor else None,
            anchor_character_start=anchor.character_start if anchor else None,
            anchor_character_end=anchor.character_end if anchor else None,
            anchor_content_hash=anchor.content_hash if anchor else None,
            strength=evidence.strength.value,
        )

    @staticmethod
    def to_domain(model: ClaimEvidenceModel) -> Evidence:
        """Convert an ORM ClaimEvidenceModel into a domain Evidence."""
        try:
            evidence_type = EvidenceType(model.evidence_type)
        except ValueError:
            evidence_type = EvidenceType.ARTICLE_TEXT

        try:
            strength = EvidenceStrength(model.strength)
        except ValueError:
            strength = EvidenceStrength.MODERATE

        anchor = None
        if (
            model.anchor_sentence_index is not None
            or model.anchor_paragraph_index is not None
            or model.anchor_character_start is not None
            or model.anchor_character_end is not None
            or model.anchor_content_hash is not None
        ):
            anchor = EvidenceAnchor(
                sentence_index=model.anchor_sentence_index,
                paragraph_index=model.anchor_paragraph_index,
                character_start=model.anchor_character_start,
                character_end=model.anchor_character_end,
                content_hash=model.anchor_content_hash,
            )

        return Evidence(
            id=UUID(model.id),
            claim_id=UUID(model.claim_id),
            article_id=UUID(model.article_id),
            evidence_type=evidence_type,
            excerpt=model.excerpt,
            source_location=model.source_location,
            anchor=anchor,
            strength=strength,
            created_at=model.created_at,
        )


__all__ = ["EvidenceMapper"]
