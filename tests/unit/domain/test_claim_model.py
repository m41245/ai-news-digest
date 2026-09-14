"""
Unit tests for M81 claim and evidence domain models.
"""

from __future__ import annotations

import pytest
from uuid import uuid4

from ai_news_digest.domain.enums.claim_status import ClaimStatus
from ai_news_digest.domain.enums.claim_type import ClaimType
from ai_news_digest.domain.enums.evidence_strength import EvidenceStrength
from ai_news_digest.domain.enums.evidence_type import EvidenceType
from ai_news_digest.domain.models.claim import Claim
from ai_news_digest.domain.models.evidence import Evidence, EvidenceAnchor


class TestClaim:
    def test_create_claim(self) -> None:
        article_id = uuid4()
        source_id = uuid4()
        claim = Claim.create(
            article_id=article_id,
            source_id=source_id,
            claim_text="OpenAI released GPT-5.",
            claim_type=ClaimType.ANNOUNCEMENT,
            confidence=0.9,
        )
        assert claim.article_id == article_id
        assert claim.source_id == source_id
        assert claim.claim_text == "OpenAI released GPT-5."
        assert claim.claim_type == ClaimType.ANNOUNCEMENT
        assert claim.confidence == 0.9
        assert claim.status == ClaimStatus.UNVERIFIED
        assert claim.evidence_support_score is None
        assert claim.schema_version == "v1"

    def test_claim_defaults(self) -> None:
        article_id = uuid4()
        source_id = uuid4()
        claim = Claim.create(
            article_id=article_id,
            source_id=source_id,
            claim_text="Some claim.",
        )
        assert claim.claim_type == ClaimType.OTHER
        assert claim.confidence is None
        assert claim.status == ClaimStatus.UNVERIFIED
        assert claim.prompt_version is None
        assert claim.ai_provider is None

    def test_update_status(self) -> None:
        claim = Claim.create(
            article_id=uuid4(),
            source_id=uuid4(),
            claim_text="Test claim.",
        )
        claim.update_status(ClaimStatus.SUPPORTED, evidence_support_score=0.85)
        assert claim.status == ClaimStatus.SUPPORTED
        assert claim.evidence_support_score == 0.85

    def test_update_status_clamps_score(self) -> None:
        claim = Claim.create(
            article_id=uuid4(),
            source_id=uuid4(),
            claim_text="Test claim.",
        )
        claim.update_status(ClaimStatus.SUPPORTED, evidence_support_score=1.5)
        assert claim.evidence_support_score == 1.0
        claim.update_status(ClaimStatus.UNSUPPORTED, evidence_support_score=-0.5)
        assert claim.evidence_support_score == 0.0


class TestEvidence:
    def test_create_evidence(self) -> None:
        claim_id = uuid4()
        article_id = uuid4()
        evidence = Evidence.create(
            claim_id=claim_id,
            article_id=article_id,
            evidence_type=EvidenceType.ARTICLE_TEXT,
            excerpt="OpenAI released GPT-5 today.",
            source_location="paragraph 2",
            strength=EvidenceStrength.STRONG,
        )
        assert evidence.claim_id == claim_id
        assert evidence.article_id == article_id
        assert evidence.evidence_type == EvidenceType.ARTICLE_TEXT
        assert evidence.excerpt == "OpenAI released GPT-5 today."
        assert evidence.source_location == "paragraph 2"
        assert evidence.strength == EvidenceStrength.STRONG
        assert evidence.is_bounded() is True

    def test_evidence_with_anchor(self) -> None:
        claim_id = uuid4()
        article_id = uuid4()
        anchor = EvidenceAnchor(
            sentence_index=2,
            paragraph_index=1,
            character_start=100,
            character_end=200,
            content_hash="abc123",
        )
        evidence = Evidence.create(
            claim_id=claim_id,
            article_id=article_id,
            anchor=anchor,
        )
        assert evidence.anchor is not None
        assert evidence.anchor.sentence_index == 2
        assert evidence.anchor.paragraph_index == 1
        assert evidence.anchor.character_start == 100
        assert evidence.anchor.character_end == 200
        assert evidence.anchor.content_hash == "abc123"

    def test_evidence_bounded(self) -> None:
        evidence = Evidence.create(
            claim_id=uuid4(),
            article_id=uuid4(),
            excerpt="short",
        )
        assert evidence.is_bounded() is True

    def test_evidence_unbounded(self) -> None:
        long_excerpt = "x" * 600
        evidence = Evidence.create(
            claim_id=uuid4(),
            article_id=uuid4(),
            excerpt=long_excerpt,
        )
        assert evidence.is_bounded() is False


__all__ = ["TestClaim", "TestEvidence"]
