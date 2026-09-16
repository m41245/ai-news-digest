"""
Unit tests for IntelligenceQualityService (M92).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_news_digest.application.services.intelligence_quality_service import (
    IntelligenceQualityService,
    QualityFlag,
)
from ai_news_digest.domain.models.claim import Claim
from ai_news_digest.domain.models.evidence import Evidence
from ai_news_digest.domain.models.relationship import (
    ProvenanceSource,
    Relationship,
)
from ai_news_digest.domain.models.story_cluster import StoryCluster


class TestIntelligenceQualityService:
    """Tests for IntelligenceQualityService."""

    def setup_method(self) -> None:
        self.service = IntelligenceQualityService()
        self.now = datetime.now(UTC)

    def test_evaluate_claim_no_evidence(self) -> None:
        claim = Claim(
            id=uuid4(),
            article_id=uuid4(),
            source_id=uuid4(),
            claim_text="Test claim",
            status="unverified",
        )
        result = self.service.evaluate_claim(claim, evidence_items=[], conflicts=[])
        assert QualityFlag.MISSING_EVIDENCE.value in result.flags
        assert QualityFlag.UNVERIFIED_CLAIM.value in result.flags
        assert result.evidence_count == 0
        assert result.overall_score >= 0.0
        assert result.overall_score <= 1.0

    def test_evaluate_claim_with_evidence(self) -> None:
        claim = Claim(
            id=uuid4(),
            article_id=uuid4(),
            source_id=uuid4(),
            claim_text="Test claim",
            status="supported",
            confidence=0.9,
        )
        evidence = Evidence(
            id=uuid4(),
            claim_id=claim.id,
            article_id=uuid4(),
            evidence_type="article_text",
            strength="strong",
        )
        result = self.service.evaluate_claim(
            claim, evidence_items=[evidence], conflicts=[]
        )
        assert QualityFlag.MISSING_EVIDENCE.value not in result.flags
        assert result.evidence_count == 1

    def test_evaluate_claim_with_conflicts(self) -> None:
        claim = Claim(
            id=uuid4(),
            article_id=uuid4(),
            source_id=uuid4(),
            claim_text="Test claim",
            status="supported",
        )
        conflict = type("Conflict", (), {
            "claim_a_id": claim.id,
            "claim_b_id": uuid4(),
        })()
        result = self.service.evaluate_claim(claim, evidence_items=[], conflicts=[conflict])
        assert QualityFlag.CONFLICTING_EVIDENCE.value in result.flags
        assert result.conflict_present is True

    def test_evaluate_claim_low_confidence(self) -> None:
        claim = Claim(
            id=uuid4(),
            article_id=uuid4(),
            source_id=uuid4(),
            claim_text="Test claim",
            status="supported",
            confidence=0.2,
        )
        result = self.service.evaluate_claim(claim)
        assert QualityFlag.LOW_CONFIDENCE.value in result.flags

    def test_evaluate_relationship_verified(self) -> None:
        rel = Relationship.create(
            subject_entity_type="company",
            subject_entity_id=uuid4(),
            relationship_type="partners_with",
            object_entity_type="company",
            object_entity_id=uuid4(),
            status="verified",
            confidence=0.9,
            provenance_source=ProvenanceSource.DETERMINISTIC,
            source_count=3,
        )
        result = self.service.evaluate_relationship(rel)
        assert result.conflict_present is False
        assert "verified" in result.explanation.lower()
        assert result.source_count == 3

    def test_evaluate_relationship_disputed(self) -> None:
        rel = Relationship.create(
            subject_entity_type="company",
            subject_entity_id=uuid4(),
            relationship_type="partners_with",
            object_entity_type="company",
            object_entity_id=uuid4(),
            status="disputed",
            confidence=0.9,
            provenance_source=ProvenanceSource.DETERMINISTIC,
        )
        result = self.service.evaluate_relationship(rel)
        assert QualityFlag.CONFLICTING_EVIDENCE.value in result.flags
        assert result.conflict_present is True

    def test_evaluate_relationship_single_source(self) -> None:
        rel = Relationship.create(
            subject_entity_type="company",
            subject_entity_id=uuid4(),
            relationship_type="partners_with",
            object_entity_type="company",
            object_entity_id=uuid4(),
            status="verified",
            confidence=0.9,
            provenance_source=ProvenanceSource.DETERMINISTIC,
            source_count=1,
        )
        result = self.service.evaluate_relationship(rel)
        assert QualityFlag.SINGLE_SOURCE.value in result.flags

    def test_evaluate_story_cluster_multiple_sources(self) -> None:
        cluster = StoryCluster(
            id=uuid4(),
            title="Test",
            slug="test",
            importance_score=0.8,
            confidence=0.9,
        )
        result = self.service.evaluate_story_cluster(
            cluster=cluster,
            article_count=5,
            source_count=3,
            evidence_count=10,
            conflict_count=0,
        )
        assert QualityFlag.SINGLE_SOURCE.value not in result.flags
        assert result.evidence_count == 5
        assert result.source_count == 3

    def test_evaluate_story_cluster_with_conflicts(self) -> None:
        cluster = StoryCluster(
            id=uuid4(),
            title="Test",
            slug="test",
        )
        result = self.service.evaluate_story_cluster(
            cluster=cluster,
            article_count=3,
            source_count=2,
            evidence_count=5,
            conflict_count=3,
        )
        assert QualityFlag.CONFLICTING_EVIDENCE.value in result.flags
        assert QualityFlag.HIGH_CONFLICT.value in result.flags

    def test_evaluate_trend_single_source(self) -> None:
        trend = type("Trend", (), {
            "id": uuid4(),
            "source_count": 1,
            "story_count": 3,
            "last_detected_at": datetime.now(UTC),
        })()
        result = self.service.evaluate_trend(trend)
        assert QualityFlag.SINGLE_SOURCE.value in result.flags

    def test_quality_score_bounds(self) -> None:
        claim = Claim(
            id=uuid4(),
            article_id=uuid4(),
            source_id=uuid4(),
            claim_text="Test claim",
        )
        result = self.service.evaluate_claim(claim, evidence_items=[], conflicts=[])
        assert 0.0 <= result.overall_score <= 1.0

    def test_freshness_very_recent(self) -> None:
        claim = Claim(
            id=uuid4(),
            article_id=uuid4(),
            source_id=uuid4(),
            claim_text="Test claim",
            created_at=datetime.now(UTC),
        )
        result = self.service.evaluate_claim(claim)
        assert result.freshness in ("very_recent", "recent")

    def test_freshness_stale(self) -> None:
        old_date = datetime.now(UTC).replace(year=2020)
        claim = Claim(
            id=uuid4(),
            article_id=uuid4(),
            source_id=uuid4(),
            claim_text="Test claim",
            created_at=old_date,
        )
        result = self.service.evaluate_claim(claim)
        assert result.freshness in ("stale", "very_stale")


__all__ = ["TestIntelligenceQualityService"]
