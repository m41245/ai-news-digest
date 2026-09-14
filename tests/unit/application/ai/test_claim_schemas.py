"""
Unit tests for M81 claim schemas.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.ai.claim_schemas import (
    ClaimSchema,
    EvidenceAnchorSchema,
    EvidenceSchema,
    StructuredClaimsOutput,
    validate_claims_output,
)
from ai_news_digest.domain.enums.claim_type import ClaimType
from ai_news_digest.domain.enums.evidence_type import EvidenceType


class TestClaimSchema:
    def test_valid_claim(self) -> None:
        claim = ClaimSchema(
            claim="OpenAI released GPT-5.",
            type=ClaimType.ANNOUNCEMENT,
            confidence=0.9,
        )
        assert claim.claim == "OpenAI released GPT-5."
        assert claim.type == ClaimType.ANNOUNCEMENT
        assert claim.confidence == 0.9
        assert claim.evidence == []

    def test_empty_claim_raises(self) -> None:
        with pytest.raises(ValueError, match="claim must not be empty"):
            ClaimSchema(claim="")

    def test_whitespace_claim_raises(self) -> None:
        with pytest.raises(ValueError, match="claim must not be empty"):
            ClaimSchema(claim="   ")

    def test_claim_truncated(self) -> None:
        long_claim = "x" * 1001
        claim = ClaimSchema(claim=long_claim)
        assert len(claim.claim) == 1000

    def test_confidence_clamped(self) -> None:
        claim = ClaimSchema(claim="Test", confidence=1.5)
        assert claim.confidence == 1.0
        claim = ClaimSchema(claim="Test", confidence=-0.5)
        assert claim.confidence == 0.0


class TestEvidenceSchema:
    def test_valid_evidence(self) -> None:
        evidence = EvidenceSchema(
            evidence_type=EvidenceType.ARTICLE_TEXT,
            excerpt="OpenAI released GPT-5.",
            source_location="paragraph 2",
        )
        assert evidence.evidence_type == EvidenceType.ARTICLE_TEXT
        assert evidence.excerpt == "OpenAI released GPT-5."

    def test_excerpt_truncated(self) -> None:
        long_excerpt = "x" * 501
        evidence = EvidenceSchema(excerpt=long_excerpt)
        assert len(evidence.excerpt) == 500

    def test_none_excerpt(self) -> None:
        evidence = EvidenceSchema(excerpt=None)
        assert evidence.excerpt is None

    def test_empty_excerpt_returns_none(self) -> None:
        evidence = EvidenceSchema(excerpt="")
        assert evidence.excerpt is None


class TestEvidenceAnchorSchema:
    def test_valid_anchor(self) -> None:
        anchor = EvidenceAnchorSchema(
            sentence_index=2,
            paragraph_index=1,
            character_start=100,
            character_end=200,
            content_hash="abc123",
        )
        assert anchor.sentence_index == 2
        assert anchor.paragraph_index == 1
        assert anchor.character_start == 100
        assert anchor.character_end == 200
        assert anchor.content_hash == "abc123"

    def test_empty_anchor(self) -> None:
        anchor = EvidenceAnchorSchema()
        assert anchor.sentence_index is None
        assert anchor.paragraph_index is None


class TestStructuredClaimsOutput:
    def test_valid_output(self) -> None:
        data = {
            "claims": [
                {
                    "claim": "OpenAI released GPT-5.",
                    "type": "ANNOUNCEMENT",
                    "confidence": 0.9,
                    "evidence": [
                        {
                            "evidence_type": "ARTICLE_TEXT",
                            "excerpt": "OpenAI released GPT-5.",
                        }
                    ],
                }
            ]
        }
        output = validate_claims_output(data)
        assert len(output.claims) == 1
        assert output.claims[0].claim == "OpenAI released GPT-5."

    def test_duplicate_claims_removed(self) -> None:
        data = {
            "claims": [
                {"claim": "OpenAI released GPT-5.", "type": "ANNOUNCEMENT"},
                {"claim": "openai released gpt-5.", "type": "ANNOUNCEMENT"},
                {"claim": "Different claim.", "type": "FACT"},
            ]
        }
        output = validate_claims_output(data)
        assert len(output.claims) == 2

    def test_too_many_claims_limited(self) -> None:
        claims = [
            {"claim": f"Claim {i}", "type": "FACT"} for i in range(25)
        ]
        data = {"claims": claims}
        output = validate_claims_output(data)
        assert len(output.claims) == 20

    def test_malformed_claim_skipped(self) -> None:
        data = {
            "claims": [
                {"claim": "Valid claim.", "type": "FACT"},
                {"claim": "", "type": "FACT"},
                {"type": "FACT"},
            ]
        }
        output = validate_claims_output(data)
        assert len(output.claims) == 1

    def test_non_dict_raises(self) -> None:
        with pytest.raises(ValueError, match="Claims response must be a JSON object"):
            validate_claims_output([1, 2, 3])

    def test_missing_claims_key(self) -> None:
        output = validate_claims_output({})
        assert output.claims == ()


__all__ = [
    "TestClaimSchema",
    "TestEvidenceSchema",
    "TestEvidenceAnchorSchema",
    "TestStructuredClaimsOutput",
]
