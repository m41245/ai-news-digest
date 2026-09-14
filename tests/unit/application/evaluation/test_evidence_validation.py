"""
Unit tests for M81 evidence validation.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.evaluation.evidence_validation import (
    compute_claim_status,
    compute_evidence_support_score,
    validate_excerpt_in_source,
)


class TestComputeEvidenceSupportScore:
    def test_no_evidence_returns_zero(self) -> None:
        score = compute_evidence_support_score(
            source_content="some content",
            evidence_list=[],
        )
        assert score == 0.0

    def test_no_source_content_returns_low(self) -> None:
        score = compute_evidence_support_score(
            source_content=None,
            evidence_list=[{"excerpt": "something"}],
        )
        assert score == 0.1

    def test_exact_excerpt_match(self) -> None:
        evidence = [{"excerpt": "OpenAI released GPT-5."}]
        score = compute_evidence_support_score(
            source_content="Today OpenAI released GPT-5. This is a major milestone.",
            evidence_list=evidence,
        )
        assert score >= 0.6

    def test_no_excerpt_match(self) -> None:
        evidence = [{"excerpt": "Not in source."}]
        score = compute_evidence_support_score(
            source_content="Some other content here.",
            evidence_list=evidence,
        )
        assert score < 0.5

    def test_multiple_evidence_increases_score(self) -> None:
        evidence = [
            {"excerpt": "OpenAI released GPT-5."},
            {"excerpt": "This is a major milestone."},
        ]
        score = compute_evidence_support_score(
            source_content="OpenAI released GPT-5. This is a major milestone for AI.",
            evidence_list=evidence,
        )
        assert score >= 0.5

    def test_short_excerpt_ignored(self) -> None:
        evidence = [{"excerpt": "hi"}]
        score = compute_evidence_support_score(
            source_content="Some content.",
            evidence_list=evidence,
        )
        assert score == 0.0

    def test_has_location_bonus(self) -> None:
        evidence = [
            {
                "excerpt": "OpenAI released GPT-5.",
                "source_location": "paragraph 2",
            }
        ]
        score = compute_evidence_support_score(
            source_content="OpenAI released GPT-5. This is major.",
            evidence_list=evidence,
        )
        assert score >= 0.5

    def test_score_capped_at_one(self) -> None:
        evidence = [
            {
                "excerpt": "OpenAI released GPT-5.",
                "source_location": "para 1",
            },
            {
                "excerpt": "This is a major milestone.",
                "source_location": "para 2",
            },
        ]
        score = compute_evidence_support_score(
            source_content="OpenAI released GPT-5. This is a major milestone. More text.",
            evidence_list=evidence,
        )
        assert score <= 1.0


class TestValidateExcerptInSource:
    def test_excerpt_found(self) -> None:
        assert (
            validate_excerpt_in_source(
                "OpenAI released GPT-5.",
                "Today OpenAI released GPT-5. This is major.",
            )
            is True
        )

    def test_excerpt_not_found(self) -> None:
        assert (
            validate_excerpt_in_source(
                "Not in source.",
                "Some other content.",
            )
            is False
        )

    def test_short_excerpt_returns_false(self) -> None:
        assert validate_excerpt_in_source("hi", "Some content.") is False

    def test_none_excerpt_returns_false(self) -> None:
        assert validate_excerpt_in_source(None, "Some content.") is False

    def test_none_content_returns_false(self) -> None:
        assert validate_excerpt_in_source("Some excerpt.", None) is False


class TestComputeClaimStatus:
    def test_high_score_is_supported(self) -> None:
        assert compute_claim_status(0.8) == "supported"
        assert compute_claim_status(1.0) == "supported"

    def test_medium_score_is_partially_supported(self) -> None:
        assert compute_claim_status(0.5) == "partially_supported"
        assert compute_claim_status(0.4) == "partially_supported"

    def test_low_score_is_unsupported(self) -> None:
        assert compute_claim_status(0.1) == "unsupported"

    def test_zero_score_is_unverified(self) -> None:
        assert compute_claim_status(0.0) == "unverified"

    def test_none_score_is_unverified(self) -> None:
        assert compute_claim_status(None) == "unverified"

    def test_zero_score_is_unverified(self) -> None:
        assert compute_claim_status(0.0) == "unverified"


__all__ = [
    "TestComputeEvidenceSupportScore",
    "TestValidateExcerptInSource",
    "TestComputeClaimStatus",
]
