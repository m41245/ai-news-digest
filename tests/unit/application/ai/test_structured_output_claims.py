"""
Unit tests for M81 structured output with claims.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.ai.structured_output import (
    StructuredIntelligence,
    validate_structured_output,
)


class TestStructuredIntelligenceWithClaims:
    def test_default_claims_empty(self) -> None:
        obj = StructuredIntelligence(summary="A summary.")
        assert obj.claims == ()

    def test_with_claims(self) -> None:
        from ai_news_digest.application.ai.claim_schemas import ClaimSchema

        claim = ClaimSchema(claim="OpenAI released GPT-5.", type="ANNOUNCEMENT")
        obj = StructuredIntelligence(summary="A summary.", claims=[claim])
        assert len(obj.claims) == 1
        assert obj.claims[0].claim == "OpenAI released GPT-5."

    def test_invalid_claims_default_to_empty(self) -> None:
        obj = validate_structured_output(
            {"summary": "s", "claims": "not-a-list"}
        )
        assert obj.claims == ()


class TestValidateStructuredOutputWithClaims:
    def test_valid_response_with_claims(self) -> None:
        data = {
            "summary": "A summary.",
            "claims": [
                {
                    "claim": "OpenAI released GPT-5.",
                    "type": "ANNOUNCEMENT",
                    "confidence": 0.9,
                }
            ],
        }
        obj = validate_structured_output(data)
        assert len(obj.claims) == 1
        assert obj.claims[0].claim == "OpenAI released GPT-5."

    def test_missing_claims_key(self) -> None:
        data = {"summary": "A summary."}
        obj = validate_structured_output(data)
        assert obj.claims == ()

    def test_empty_claims_list(self) -> None:
        data = {"summary": "A summary.", "claims": []}
        obj = validate_structured_output(data)
        assert obj.claims == ()


__all__ = ["TestStructuredIntelligenceWithClaims", "TestValidateStructuredOutputWithClaims"]
