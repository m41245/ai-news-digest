"""
Unit tests for M80 benchmark evaluator.
"""

from __future__ import annotations

import json

from ai_news_digest.application.ai.benchmark.evaluator import (
    BenchmarkEvaluator,
    EvaluationContext,
)
from ai_news_digest.application.ai.benchmark.models import (
    BenchmarkCase,
    BenchmarkTask,
)


def _make_context(
    case: BenchmarkCase,
    raw_content: str = "{}",
    parsed: dict | None = None,
) -> EvaluationContext:
    return EvaluationContext(
        case=case,
        provider_id="test-provider",
        model="test-model",
        raw_content=raw_content,
        parsed_structured=parsed,
        latency_ms=100.0,
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        estimated_cost=0.001,
        cost_known=True,
        usage_known=True,
    )


class TestStructuredOutputValidity:
    def test_valid_json_passes(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY,
            article_title="Test",
            article_content="Content.",
        )
        raw = json.dumps({"summary": "A summary.", "categories": ["ai_research"]})
        ctx = _make_context(case, raw_content=raw, parsed=json.loads(raw))
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 1.0

    def test_malformed_json_fails(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY,
            article_title="Test",
            article_content="Content.",
        )
        ctx = _make_context(case, raw_content="not json")
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 0.0
        assert "malformed_json" in result.quality_score.details.get("reason", "")

    def test_empty_output_fails(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY,
            article_title="Test",
            article_content="Content.",
        )
        ctx = _make_context(case, raw_content="")
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 0.0

    def test_missing_summary_fails(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY,
            article_title="Test",
            article_content="Content.",
        )
        raw = json.dumps({"categories": ["ai_research"]})
        ctx = _make_context(case, raw_content=raw, parsed=json.loads(raw))
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 0.0


class TestSummaryEvaluation:
    def test_good_summary_scores_high(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.SUMMARY,
            article_title="OpenAI Releases GPT-5",
            article_content=(
                "OpenAI announced GPT-5 with improved reasoning. "
                "The model is available via API. Competitors include "
                "Anthropic and Google DeepMind who are expected to "
                "respond with their own updates."
            ),
            reference_summary="OpenAI released GPT-5 with improved reasoning.",
        )
        parsed = {
            "summary": (
                "OpenAI released a new model called GPT-5 that improves "
                "reasoning and is available through API access for developers."
            )
        }
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score > 0.5

    def test_empty_summary_scores_zero(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.SUMMARY,
            article_title="Test",
            article_content="Content.",
        )
        parsed = {"summary": ""}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 0.0

    def test_high_input_copy_penalized(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.SUMMARY,
            article_title="Test",
            article_content="This is a very long article. " * 200,
        )
        parsed = {"summary": "This is a very long article. " * 200}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.details.get("input_copy_ratio", 0) > 0.8


class TestKeyTakeawaysEvaluation:
    def test_good_takeaways(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.KEY_TAKEAWAYS,
            article_title="Test",
            article_content="Content.",
            reference_key_takeaways=("point one", "point two", "point three"),
        )
        parsed = {
            "key_takeaways": ["Point one.", "Point two.", "Point three."],
            "summary": "Summary.",
        }
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score > 0.5

    def test_empty_takeaways_scores_zero(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.KEY_TAKEAWAYS,
            article_title="Test",
            article_content="Content.",
        )
        parsed = {"key_takeaways": []}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 0.0

    def test_duplicate_takeaways_penalized(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.KEY_TAKEAWAYS,
            article_title="Test",
            article_content="Content.",
        )
        parsed = {
            "key_takeaways": ["same thing here", "same thing here", "same thing here"],
            "summary": "Summary.",
        }
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert "duplicates_detected" in result.quality_score.details.get("reasons", [])


class TestWhyItMattersEvaluation:
    def test_good_why_it_matters(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.WHY_IT_MATTERS,
            article_title="Test",
            article_content="Content.",
            reference_why_it_matters="This matters because it changes the industry.",
        )
        parsed = {"why_it_matters": "This matters because it changes the industry."}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score > 0.5

    def test_empty_why_it_matters_scores_zero(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.WHY_IT_MATTERS,
            article_title="Test",
            article_content="Content.",
        )
        parsed = {"why_it_matters": ""}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 0.0


class TestCategoryEvaluation:
    def test_exact_match(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.CATEGORIES,
            article_title="Test",
            article_content="Content.",
            expected_categories=("ai_research",),
        )
        parsed = {"categories": ["ai_research"]}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 1.0

    def test_normalized_match(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.CATEGORIES,
            article_title="Test",
            article_content="Content.",
            expected_categories=("ai_research",),
        )
        parsed = {"categories": ["AI Research"]}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 1.0

    def test_unknown_category_falls_back(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.CATEGORIES,
            article_title="Test",
            article_content="Content.",
            expected_categories=("ai_research",),
        )
        parsed = {"categories": ["unknown_category"]}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score < 1.0


class TestCompanyEvaluation:
    def test_exact_match(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.COMPANIES,
            article_title="Test",
            article_content="Content.",
            expected_companies=("OpenAI",),
        )
        parsed = {"companies": ["OpenAI"]}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 1.0

    def test_alias_match(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.COMPANIES,
            article_title="Test",
            article_content="Content.",
            expected_companies=("OpenAI",),
        )
        parsed = {"companies": ["openai"]}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 1.0

    def test_case_insensitive(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.COMPANIES,
            article_title="Test",
            article_content="Content.",
            expected_companies=("OpenAI",),
        )
        parsed = {"companies": ["OPENAI"]}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 1.0


class TestTopicEvaluation:
    def test_exact_match(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.TOPICS,
            article_title="Test",
            article_content="Content.",
            expected_topics=("large language models",),
        )
        parsed = {"topics": ["large language models"]}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 1.0

    def test_normalized_match(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.TOPICS,
            article_title="Test",
            article_content="Content.",
            expected_topics=("large language models",),
        )
        parsed = {"topics": ["Large Language Models"]}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 1.0

    def test_no_expected_topics(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.TOPICS,
            article_title="Test",
            article_content="Content.",
            expected_topics=(),
        )
        parsed = {"topics": []}
        ctx = _make_context(case, parsed=parsed)
        result = BenchmarkEvaluator().evaluate(ctx)
        assert result.quality_score.score == 1.0


class TestRepetitionDetection:
    def test_no_repetition(self):
        evaluator = BenchmarkEvaluator()
        assert not evaluator._has_repetition(
            "This is a normal summary without any repetition at all in the text."
        )

    def test_high_repetition_detected(self):
        evaluator = BenchmarkEvaluator()
        text = "word word word word word word word word word word word word word word word word"
        assert evaluator._has_repetition(text)
