"""
Unit tests for M81 claim normalization.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.evaluation.claim_normalizer import (
    deduplicate_claims,
    normalize_claim_text,
)


class TestNormalizeClaimText:
    def test_strips_whitespace(self) -> None:
        assert normalize_claim_text("  hello world  ") == "hello world"

    def test_lowercases(self) -> None:
        assert normalize_claim_text("HELLO WORLD") == "hello world"

    def test_removes_punctuation(self) -> None:
        assert normalize_claim_text("Hello, world!") == "hello world"

    def test_collapses_whitespace(self) -> None:
        assert normalize_claim_text("hello   world") == "hello world"

    def test_preserves_hyphens(self) -> None:
        assert "state-of-the-art" in normalize_claim_text("state-of-the-art")

    def test_preserves_slashes(self) -> None:
        assert "ai/ml" in normalize_claim_text("AI/ML")


class TestDeduplicateClaims:
    def test_removes_duplicates(self) -> None:
        claims = [
            {"claim": "OpenAI released GPT-5."},
            {"claim": "OpenAI released GPT-5."},
        ]
        result = deduplicate_claims(claims)
        assert len(result) == 1

    def test_case_insensitive_dedup(self) -> None:
        claims = [
            {"claim": "OpenAI released GPT-5."},
            {"claim": "openai released gpt-5."},
        ]
        result = deduplicate_claims(claims)
        assert len(result) == 1

    def test_preserves_distinct_claims(self) -> None:
        claims = [
            {"claim": "OpenAI released GPT-5."},
            {"claim": "Google released Gemini 2."},
        ]
        result = deduplicate_claims(claims)
        assert len(result) == 2

    def test_removes_empty_claims(self) -> None:
        claims = [
            {"claim": "Valid claim."},
            {"claim": ""},
            {"claim": "   "},
        ]
        result = deduplicate_claims(claims)
        assert len(result) == 1

    def test_empty_list_returns_empty(self) -> None:
        assert deduplicate_claims([]) == []

    def test_missing_claim_key_skipped(self) -> None:
        claims = [
            {"claim": "Valid claim."},
            {"type": "FACT"},
        ]
        result = deduplicate_claims(claims)
        assert len(result) == 1


__all__ = ["TestNormalizeClaimText", "TestDeduplicateClaims"]
