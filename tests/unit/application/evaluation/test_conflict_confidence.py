"""
Unit tests for M82 conflict confidence model.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.evaluation.conflict_confidence import (
    ConflictConfidenceFactors,
    compute_conflict_confidence,
)
from ai_news_digest.domain.enums.conflict_type import ConflictType


class TestComputeConflictConfidence:
    def test_baseline(self) -> None:
        factors = ConflictConfidenceFactors()
        confidence = compute_conflict_confidence(factors, ConflictType.NUMERIC)
        assert confidence == 0.0

    def test_entity_match_boosts(self) -> None:
        factors = ConflictConfidenceFactors(entity_match=True)
        confidence = compute_conflict_confidence(factors, ConflictType.NUMERIC)
        assert confidence == 0.3

    def test_all_factors_max_confidence(self) -> None:
        factors = ConflictConfidenceFactors(
            entity_match=True,
            claim_type_compatible=True,
            temporal_compatible=True,
            numeric_mismatch=True,
            evidence_support_a=1.0,
            evidence_support_b=1.0,
            source_independent=True,
            llm_agreement=True,
        )
        confidence = compute_conflict_confidence(factors, ConflictType.NUMERIC)
        assert confidence == 1.0

    def test_clamped_to_one(self) -> None:
        factors = ConflictConfidenceFactors(
            entity_match=True,
            claim_type_compatible=True,
            temporal_compatible=True,
            numeric_mismatch=True,
            evidence_support_a=1.0,
            evidence_support_b=1.0,
            source_independent=True,
            llm_agreement=True,
        )
        confidence = compute_conflict_confidence(factors, ConflictType.NUMERIC)
        assert confidence <= 1.0

    def test_evidence_support_boost(self) -> None:
        factors = ConflictConfidenceFactors(
            entity_match=True,
            evidence_support_a=1.0,
            evidence_support_b=1.0,
        )
        confidence = compute_conflict_confidence(factors, ConflictType.OTHER)
        assert 0.3 <= confidence <= 0.5

    def test_date_mismatch_boost(self) -> None:
        factors = ConflictConfidenceFactors(
            entity_match=True,
            claim_type_compatible=True,
            date_mismatch=True,
        )
        confidence = compute_conflict_confidence(factors, ConflictType.DATE)
        assert confidence >= 0.6

    def test_event_state_mismatch_boost(self) -> None:
        factors = ConflictConfidenceFactors(
            entity_match=True,
            claim_type_compatible=True,
            event_state_mismatch=True,
        )
        confidence = compute_conflict_confidence(factors, ConflictType.EVENT_STATUS)
        assert confidence >= 0.65


__all__ = ["TestComputeConflictConfidence"]
