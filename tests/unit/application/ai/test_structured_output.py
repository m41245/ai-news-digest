"""
Unit tests for structured AI output validation.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.ai.structured_output import (
    StructuredIntelligence,
    validate_structured_output,
)


class TestStructuredIntelligence:
    def test_valid_defaults(self) -> None:
        obj = StructuredIntelligence(summary="A summary.", why_it_matters="Important.")
        assert obj.summary == "A summary."
        assert obj.key_takeaways == ()
        assert obj.why_it_matters == "Important."
        assert obj.categories == ()
        assert obj.companies == ()
        assert obj.topics == ()
        assert obj.confidence is None
        assert obj.importance is None

    def test_empty_summary_raises(self) -> None:
        with pytest.raises(ValueError, match="summary must not be empty"):
            StructuredIntelligence(summary="")

    def test_whitespace_summary_raises(self) -> None:
        with pytest.raises(ValueError, match="summary must not be empty"):
            StructuredIntelligence(summary="   ")

    def test_summary_stripped(self) -> None:
        obj = StructuredIntelligence(summary="  trimmed  ")
        assert obj.summary == "trimmed"

    def test_empty_why_it_matters_raises(self) -> None:
        with pytest.raises(ValueError, match="why_it_matters must not be empty"):
            StructuredIntelligence(summary="s", why_it_matters="")

    def test_why_it_matters_truncated(self) -> None:
        long_text = "x" * 2001
        obj = StructuredIntelligence(summary="s", why_it_matters=long_text)
        assert len(obj.why_it_matters) == 2000

    def test_too_many_takeaways_raises(self) -> None:
        with pytest.raises(ValueError, match="key_takeaways"):
            StructuredIntelligence(summary="s", key_takeaways=["t"] * 9)

    def test_takeaway_truncated(self) -> None:
        obj = StructuredIntelligence(summary="s", key_takeaways=["x" * 301])
        assert len(obj.key_takeaways[0]) == 300

    def test_empty_takeaway_removed(self) -> None:
        obj = StructuredIntelligence(summary="s", key_takeaways=["valid", "", "also valid"])
        assert obj.key_takeaways == ("valid", "also valid")

    def test_confidence_clamped(self) -> None:
        obj = StructuredIntelligence(summary="s", confidence=1.5)
        assert obj.confidence == 1.0
        obj = StructuredIntelligence(summary="s", confidence=-0.5)
        assert obj.confidence == 0.0

    def test_importance_clamped(self) -> None:
        obj = StructuredIntelligence(summary="s", importance=2.0)
        assert obj.importance == 1.0

    def test_categories_deduplicated(self) -> None:
        obj = StructuredIntelligence(summary="s", categories=("ai_research", "AI_Research"))
        assert obj.categories == ("ai_research",)

    def test_categories_limited(self) -> None:
        obj = StructuredIntelligence(summary="s", categories=[f"cat_{i}" for i in range(10)])
        assert len(obj.categories) == 5

    def test_companies_deduplicated(self) -> None:
        obj = StructuredIntelligence(summary="s", companies=("OpenAI", "openai"))
        assert obj.companies == ("OpenAI",)

    def test_companies_limited(self) -> None:
        obj = StructuredIntelligence(summary="s", companies=[f"co_{i}" for i in range(15)])
        assert len(obj.companies) == 10

    def test_topics_deduplicated(self) -> None:
        obj = StructuredIntelligence(summary="s", topics=("GPT", "gpt"))
        assert obj.topics == ("GPT",)

    def test_topics_limited(self) -> None:
        obj = StructuredIntelligence(summary="s", topics=[f"topic_{i}" for i in range(15)])
        assert len(obj.topics) == 10

    def test_invalid_confidence_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            StructuredIntelligence(summary="s", confidence="not-a-number")

    def test_invalid_importance_raises(self) -> None:
        with pytest.raises(ValueError, match="importance"):
            StructuredIntelligence(summary="s", importance="not-a-number")

    def test_duplicate_categories_removed(self) -> None:
        obj = StructuredIntelligence(summary="s", categories=("ai_research", "ai_research", "ai_models"))
        assert obj.categories == ("ai_research", "ai_models")

    def test_duplicate_companies_removed(self) -> None:
        obj = StructuredIntelligence(summary="s", companies=("OpenAI", "openai", "Anthropic"))
        assert obj.companies == ("OpenAI", "Anthropic")

    def test_duplicate_topics_removed(self) -> None:
        obj = StructuredIntelligence(summary="s", topics=("GPT", "gpt", "AI"))
        assert obj.topics == ("GPT", "AI")

    def test_malformed_provider_output_raises(self) -> None:
        with pytest.raises(ValueError, match="summary must not be empty"):
            StructuredIntelligence(summary="", topics=["AI"])

    def test_oversized_summary_truncated(self) -> None:
        # summary is not truncated, just stripped; long summaries are allowed
        long_summary = "x" * 10000
        obj = StructuredIntelligence(summary=long_summary)
        assert obj.summary == long_summary


class TestValidateStructuredOutput:
    def test_valid_response(self) -> None:
        data = {
            "summary": "A summary.",
            "key_takeaways": ["t1"],
            "why_it_matters": "Important.",
            "categories": ["ai_research"],
            "companies": ["OpenAI"],
            "topics": ["GPT"],
            "confidence": 0.8,
            "importance": 0.9,
        }
        obj = validate_structured_output(data)
        assert obj.summary == "A summary."
        assert obj.key_takeaways == ("t1",)
        assert obj.confidence == 0.8
        assert obj.importance == 0.9

    def test_importance_score_alias(self) -> None:
        data = {
            "summary": "A summary.",
            "importance_score": 0.7,
        }
        obj = validate_structured_output(data)
        assert obj.importance == 0.7

    def test_missing_optional_fields(self) -> None:
        data = {"summary": "A summary."}
        obj = validate_structured_output(data)
        assert obj.key_takeaways == ()
        assert obj.why_it_matters is None
        assert obj.confidence is None

    def test_non_dict_raises(self) -> None:
        with pytest.raises(ValueError, match="AI response must be a JSON object"):
            validate_structured_output([1, 2, 3])

    def test_empty_summary_raises(self) -> None:
        with pytest.raises(ValueError, match="summary must not be empty"):
            validate_structured_output({"summary": ""})

    def test_oversized_field_raises(self) -> None:
        with pytest.raises(ValueError, match="key_takeaways"):
            validate_structured_output(
                {"summary": "s", "key_takeaways": ["t"] * 9}
            )

    def test_wrong_type_confidence_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_structured_output({"summary": "s", "confidence": "high"})

    def test_empty_string_why_it_matters_raises(self) -> None:
        with pytest.raises(ValueError, match="why_it_matters must not be empty"):
            validate_structured_output({"summary": "s", "why_it_matters": "   "})

    def test_oversized_categories_limited(self) -> None:
        data = {
            "summary": "s",
            "categories": [f"cat_{i}" for i in range(10)],
        }
        obj = validate_structured_output(data)
        assert len(obj.categories) == 5

    def test_duplicate_companies_removed(self) -> None:
        data = {
            "summary": "s",
            "companies": ["OpenAI", "openai", "Anthropic"],
        }
        obj = validate_structured_output(data)
        assert obj.companies == ("OpenAI", "Anthropic")

    def test_malformed_provider_output_sets_safe_defaults(self) -> None:
        data = {
            "summary": "Valid summary.",
            "key_takeaways": "not-a-list",
            "companies": None,
            "topics": {},
        }
        obj = validate_structured_output(data)
        assert obj.summary == "Valid summary."
        assert obj.companies == ()
        assert obj.topics == ()


__all__ = ["TestStructuredIntelligence", "TestValidateStructuredOutput"]
