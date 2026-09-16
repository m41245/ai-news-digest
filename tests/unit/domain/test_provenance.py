"""
Unit tests for intelligence provenance model (M92).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.claim import Claim
from ai_news_digest.domain.models.conflict import Conflict
from ai_news_digest.domain.models.evidence import Evidence
from ai_news_digest.domain.models.relationship import (
    ProvenanceSource,
    Relationship,
)
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.story_event import StoryEvent
from ai_news_digest.domain.models.trend import Trend
from ai_news_digest.domain.provenance import (
    for_article,
    for_claim,
    for_conflict,
    for_digest,
    for_evidence,
    for_relationship,
    for_story_cluster,
    for_story_event,
    for_trend,
)


class _DigestStub:
    def __init__(self) -> None:
        self.id = uuid4()
        self.article_ids = [uuid4()]
        self.provider = None
        self.model = None
        self.top_story_cluster_id = None
        self.generated_at = datetime.now(UTC)


class TestProvenanceForArticle:
    def test_deterministic_article(self) -> None:
        article = Article(
            id=uuid4(),
            title="Test",
            url="https://example.com",
            summary="Summary",
            content="Content",
            source_id=uuid4(),
            category_id=None,
            published_at=datetime.now(UTC),
            fetched_at=datetime.now(UTC),
            status="ready",
        )
        provenance = for_article(article)
        assert provenance.source == ProvenanceSource.DETERMINISTIC
        assert provenance.intelligence_type.value == "article"

    def test_ai_extracted_article(self) -> None:
        article = Article(
            id=uuid4(),
            title="Test",
            url="https://example.com",
            summary="Summary",
            content="Content",
            source_id=uuid4(),
            category_id=None,
            published_at=datetime.now(UTC),
            fetched_at=datetime.now(UTC),
            status="ready",
            ai_provider="openai",
            ai_model="gpt-4",
            ai_processed_at=datetime.now(UTC),
        )
        provenance = for_article(article)
        assert provenance.source == ProvenanceSource.AI_EXTRACTED
        assert provenance.ai_provider == "openai"
        assert provenance.ai_model == "gpt-4"
        assert provenance.is_complete is True

    def test_ai_article_missing_metadata(self) -> None:
        article = Article(
            id=uuid4(),
            title="Test",
            url="https://example.com",
            summary="Summary",
            content="Content",
            source_id=uuid4(),
            category_id=None,
            published_at=datetime.now(UTC),
            fetched_at=datetime.now(UTC),
            status="ready",
            ai_provider="openai",
        )
        provenance = for_article(article)
        assert provenance.source == ProvenanceSource.AI_EXTRACTED
        assert provenance.is_complete is False
        assert "ai_model" in provenance.completeness_gaps


class TestProvenanceForClaim:
    def test_ai_extracted_claim(self) -> None:
        claim = Claim(
            id=uuid4(),
            article_id=uuid4(),
            source_id=uuid4(),
            claim_text="Test claim",
            claim_type="fact",
            confidence=0.9,
            ai_provider="openai",
            ai_model="gpt-4",
            prompt_version="v1",
        )
        provenance = for_claim(claim)
        assert provenance.source == ProvenanceSource.AI_EXTRACTED
        assert provenance.prompt_version == "v1"
        assert any("article:" in line for line in provenance.lineage)

    def test_deterministic_claim(self) -> None:
        claim = Claim(
            id=uuid4(),
            article_id=uuid4(),
            source_id=uuid4(),
            claim_text="Test claim",
        )
        provenance = for_claim(claim)
        assert provenance.source == ProvenanceSource.DETERMINISTIC


class TestProvenanceForEvidence:
    def test_deterministic_evidence(self) -> None:
        evidence = Evidence(
            id=uuid4(),
            claim_id=uuid4(),
            article_id=uuid4(),
            evidence_type="article_text",
        )
        provenance = for_evidence(evidence)
        assert provenance.source == ProvenanceSource.DETERMINISTIC
        assert any("claim:" in line for line in provenance.lineage)
        assert any("article:" in line for line in provenance.lineage)


class TestProvenanceForConflict:
    def test_conflict_provenance(self) -> None:
        conflict = Conflict(
            id=uuid4(),
            claim_a_id=uuid4(),
            claim_b_id=uuid4(),
            article_a_id=uuid4(),
            article_b_id=uuid4(),
            source_a_id=uuid4(),
            source_b_id=uuid4(),
            conflict_type="numeric",
            status="potential",
            confidence=0.8,
            explanation="Test conflict",
            detection_version="v1",
        )
        provenance = for_conflict(conflict)
        assert provenance.source == ProvenanceSource.DETERMINISTIC
        assert provenance.detection_version == "v1"
        claim_lines = [l for l in provenance.lineage if l.startswith("claim_")]
        assert len(claim_lines) == 2


class TestProvenanceForRelationship:
    def test_ai_extracted_relationship(self) -> None:
        rel = Relationship.create(
            subject_entity_type="company",
            subject_entity_id=uuid4(),
            relationship_type="partners_with",
            object_entity_type="company",
            object_entity_id=uuid4(),
            provenance_source=ProvenanceSource.AI_EXTRACTED,
            ai_provider="openai",
            ai_model="gpt-4",
            article_id=uuid4(),
        )
        provenance = for_relationship(rel)
        assert provenance.source == ProvenanceSource.AI_EXTRACTED
        assert provenance.ai_provider == "openai"

    def test_deterministic_relationship(self) -> None:
        rel = Relationship.create(
            subject_entity_type="company",
            subject_entity_id=uuid4(),
            relationship_type="partners_with",
            object_entity_type="company",
            object_entity_id=uuid4(),
            provenance_source=ProvenanceSource.DETERMINISTIC,
            article_id=uuid4(),
        )
        provenance = for_relationship(rel)
        assert provenance.source == ProvenanceSource.DETERMINISTIC


class TestProvenanceForStoryCluster:
    def test_cluster_provenance(self) -> None:
        cluster = StoryCluster(
            id=uuid4(),
            title="Test",
            slug="test",
            representative_article_id=uuid4(),
        )
        provenance = for_story_cluster(cluster)
        assert provenance.source == ProvenanceSource.DETERMINISTIC
        assert any("article:" in line for line in provenance.lineage)


class TestProvenanceForTrend:
    def test_trend_provenance(self) -> None:
        trend = Trend(
            id=uuid4(),
            trend_type="company",
            canonical_key="openai",
            display_name="OpenAI",
            status="active",
            trend_score=75.0,
            momentum_score=80.0,
            first_detected_at=datetime.now(UTC),
            last_detected_at=datetime.now(UTC),
            recent_activity=10,
            baseline_activity=5,
            source_count=3,
            story_count=5,
            event_count=2,
            explanation="Test trend",
            related_company_ids=frozenset([uuid4()]),
        )
        provenance = for_trend(trend)
        assert provenance.source == ProvenanceSource.DETERMINISTIC
        assert len(provenance.lineage) >= 1


class TestProvenanceForDigest:
    def test_deterministic_digest(self) -> None:
        digest = _DigestStub()
        provenance = for_digest(digest)
        assert provenance.source == ProvenanceSource.DETERMINISTIC

    def test_ai_digest(self) -> None:
        digest = _DigestStub()
        digest.provider = "openai"
        digest.model = "gpt-4"
        provenance = for_digest(digest)
        assert provenance.source == ProvenanceSource.AI_EXTRACTED
        assert provenance.ai_provider == "openai"


__all__ = [
    "TestProvenanceForArticle",
    "TestProvenanceForClaim",
    "TestProvenanceForConflict",
    "TestProvenanceForDigest",
    "TestProvenanceForEvidence",
    "TestProvenanceForRelationship",
    "TestProvenanceForStoryCluster",
    "TestProvenanceForTrend",
]
