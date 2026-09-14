"""
Deterministic task-specific evaluation for M80 benchmark cases.

Evaluates AI provider outputs against benchmark expectations using
only deterministic checks. No LLM-as-judge is used.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from ai_news_digest.application.ai.benchmark.models import (
    BenchmarkCase,
    BenchmarkResult,
    BenchmarkTask,
    QualityScore,
)
from ai_news_digest.application.ai.category_vocabulary import (
    normalize_category,
)
from ai_news_digest.application.ai.company_normalizer import normalize_company
from ai_news_digest.application.ai.structured_output import validate_structured_output
from ai_news_digest.application.ai.topic_normalizer import normalize_topic


@dataclass(slots=True)
class EvaluationContext:
    """Inputs required to evaluate a single benchmark result."""

    case: BenchmarkCase
    provider_id: str
    model: str
    raw_content: str
    parsed_structured: dict[str, Any] | None = None
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    cost_known: bool = False
    usage_known: bool = False
    metadata: dict[str, Any] | None = None


class BenchmarkEvaluator:
    """Deterministic evaluator for benchmark tasks."""

    def _has_repetition(self, text: str) -> bool:
        words = re.findall(r"\w+", text.lower())
        if len(words) < 8:
            return False
        counts = Counter(words)
        most_common = counts.most_common(1)
        if not most_common:
            return False
        _, count = most_common[0]
        return count > max(3, len(words) * 0.12)

    def evaluate(self, context: EvaluationContext) -> BenchmarkResult:
        """Evaluate a single provider/model output against the benchmark case."""
        case = context.case
        task = case.task
        result = BenchmarkResult(
            provider_id=context.provider_id,
            model=context.model,
            case_id=case.case_id,
            task=task,
            latency_ms=context.latency_ms,
            input_tokens=context.input_tokens,
            output_tokens=context.output_tokens,
            total_tokens=context.total_tokens,
            estimated_cost=context.estimated_cost,
            cost_known=context.cost_known,
            usage_known=context.usage_known,
        )

        if task == BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY:
            result.quality_score = self._evaluate_structured_validity(context)
            return result

        if context.parsed_structured is None:
            result.quality_score = QualityScore(
                task=task, score=0.0, details={"error": "no_parsed_output"}
            )
            return result

        if task == BenchmarkTask.SUMMARY:
            result.quality_score = self._evaluate_summary(context)
        elif task == BenchmarkTask.KEY_TAKEAWAYS:
            result.quality_score = self._evaluate_key_takeaways(context)
        elif task == BenchmarkTask.WHY_IT_MATTERS:
            result.quality_score = self._evaluate_why_it_matters(context)
        elif task == BenchmarkTask.CATEGORIES:
            result.quality_score = self._evaluate_categories(context)
        elif task == BenchmarkTask.COMPANIES:
            result.quality_score = self._evaluate_companies(context)
        elif task == BenchmarkTask.TOPICS:
            result.quality_score = self._evaluate_topics(context)
        elif task == BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY:  # type: ignore[unreachable]
            result.quality_score = self._evaluate_structured_validity(context)
        else:
            result.quality_score = QualityScore(
                task=task, score=0.0, details={"error": "unknown_task"}
            )

        return result

    def _evaluate_structured_validity(self, context: EvaluationContext) -> QualityScore:
        details: dict[str, Any] = {}
        score = 1.0
        raw = context.raw_content.strip()

        if not raw:
            details["valid"] = False
            details["reason"] = "empty_output"
            return QualityScore(
                task=BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY, score=0.0, details=details
            )

        parsed = context.parsed_structured
        if parsed is None:
            try:
                import json

                parsed = json.loads(raw)
            except Exception as exc:
                details["valid"] = False
                details["reason"] = f"malformed_json:{type(exc).__name__}"
                return QualityScore(
                    task=BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY, score=0.0, details=details
                )

        try:
            validate_structured_output(parsed)
            details["valid"] = True
            details["fields_present"] = sorted(parsed.keys())
            return QualityScore(
                task=BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY, score=1.0, details=details
            )
        except Exception as exc:
            details["valid"] = False
            details["reason"] = f"schema_validation_failed:{type(exc).__name__}"
            details["error"] = str(exc)
            score = 0.0

        return QualityScore(
            task=BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY, score=score, details=details
        )

    def _evaluate_summary(self, context: EvaluationContext) -> QualityScore:
        case = context.case
        parsed = context.parsed_structured or {}
        actual = str(parsed.get("summary", "")).strip()
        reference = (case.reference_summary or "").strip()
        details: dict[str, Any] = {"actual_length": len(actual)}

        if not actual:
            details["reason"] = "empty_summary"
            return QualityScore(task=BenchmarkTask.SUMMARY, score=0.0, details=details)

        score = 1.0
        reasons: list[str] = []

        if len(actual) > 2000:
            score -= 0.3
            reasons.append("too_long")
            details["length_penalty"] = True

        if reference:
            ref_words = set(reference.lower().split())
            actual_words = set(actual.lower().split())
            overlap = 0.0 if not ref_words else len(ref_words & actual_words) / len(ref_words)
            details["reference_overlap"] = round(overlap, 4)
            if overlap < 0.2:
                score -= 0.4
                reasons.append("low_reference_overlap")
            elif overlap < 0.5:
                score -= 0.1
                reasons.append("moderate_reference_overlap")

        input_copy_ratio = _input_copy_ratio(actual, context.case.article_content)
        details["input_copy_ratio"] = round(input_copy_ratio, 4)
        if input_copy_ratio > 0.8:
            score -= 0.5
            reasons.append("high_input_copy")

        if self._has_repetition(actual):
            score -= 0.2
            reasons.append("repetition_detected")

        score = max(0.0, score)
        details["reasons"] = reasons
        return QualityScore(task=BenchmarkTask.SUMMARY, score=score, details=details)

    def _evaluate_key_takeaways(self, context: EvaluationContext) -> QualityScore:
        case = context.case
        parsed = context.parsed_structured or {}
        actual_raw = parsed.get("key_takeaways", [])
        if actual_raw is None:
            actual_raw = []
        if isinstance(actual_raw, str):
            actual_raw = [actual_raw]
        actual = [str(t).strip() for t in actual_raw if str(t).strip()]
        reference = [t.strip() for t in (case.reference_key_takeaways or ()) if t.strip()]

        details: dict[str, Any] = {"actual_count": len(actual), "reference_count": len(reference)}
        score = 1.0
        reasons: list[str] = []

        if not actual:
            details["reason"] = "empty_takeaways"
            return QualityScore(task=BenchmarkTask.KEY_TAKEAWAYS, score=0.0, details=details)

        if len(actual) < 2:
            score -= 0.3
            reasons.append("too_few")
        if len(actual) > 8:
            score -= 0.3
            reasons.append("too_many")

        unique = _dedupe_preserving_order(actual)
        if len(unique) < len(actual):
            score -= 0.2
            reasons.append("duplicates_detected")

        if reference:
            ref_lower = [t.lower() for t in reference]
            hit_count = 0
            for ut in unique:
                ut_lower = ut.lower()
                if any(_normalized_overlap(ut_lower, rt) > 0.6 for rt in ref_lower):
                    hit_count += 1
            coverage = hit_count / len(reference) if reference else 0.0
            details["reference_coverage"] = round(coverage, 4)
            if coverage < 0.25:
                score -= 0.4
                reasons.append("low_reference_coverage")
            elif coverage < 0.6:
                score -= 0.15
                reasons.append("moderate_reference_coverage")

        long_items = [t for t in unique if len(t) > 300]
        if long_items:
            score -= 0.1
            reasons.append("oversized_items")

        for t in unique:
            if self._has_repetition(t):
                score -= 0.1
                reasons.append("repetitive_item")
                break

        summary_text = str(parsed.get("summary", "")).strip()
        if summary_text and unique:
            overlap_with_summary = _overlap_ratio(summary_text.lower(), " ".join(unique).lower())
            details["summary_overlap"] = round(overlap_with_summary, 4)
            if overlap_with_summary > 0.85:
                score -= 0.15
                reasons.append("excessive_summary_overlap")

        score = max(0.0, score)
        details["reasons"] = reasons
        return QualityScore(task=BenchmarkTask.KEY_TAKEAWAYS, score=score, details=details)

    def _evaluate_why_it_matters(self, context: EvaluationContext) -> QualityScore:
        case = context.case
        parsed = context.parsed_structured or {}
        actual = str(parsed.get("why_it_matters", "")).strip()
        reference = (case.reference_why_it_matters or "").strip()
        details: dict[str, Any] = {"actual_length": len(actual)}

        if not actual:
            details["reason"] = "empty_why_it_matters"
            return QualityScore(task=BenchmarkTask.WHY_IT_MATTERS, score=0.0, details=details)

        score = 1.0
        reasons: list[str] = []

        if len(actual) < 20:
            score -= 0.3
            reasons.append("too_short")
        elif len(actual) > 2000:
            score -= 0.2
            reasons.append("too_long")

        if reference:
            overlap = _normalized_overlap(actual.lower(), reference.lower())
            details["reference_overlap"] = round(overlap, 4)
            if overlap < 0.15:
                score -= 0.4
                reasons.append("low_reference_overlap")
            elif overlap < 0.4:
                score -= 0.1
                reasons.append("moderate_reference_overlap")

        if self._has_repetition(actual):
            score -= 0.2
            reasons.append("repetition_detected")

        score = max(0.0, score)
        details["reasons"] = reasons
        return QualityScore(task=BenchmarkTask.WHY_IT_MATTERS, score=score, details=details)

    def _evaluate_categories(self, context: EvaluationContext) -> QualityScore:
        case = context.case
        parsed = context.parsed_structured or {}
        actual_raw = parsed.get("categories", [])
        if actual_raw is None:
            actual_raw = []
        if isinstance(actual_raw, str):
            actual_raw = [actual_raw]

        actual_norm = sorted(
            {normalize_category(str(c)).value for c in actual_raw if str(c).strip()}
        )
        expected_norm = sorted(
            {normalize_category(c).value for c in case.expected_categories if c.strip()}
        )

        details: dict[str, Any] = {"actual": actual_norm, "expected": expected_norm}

        if not expected_norm:
            if not actual_norm:
                return QualityScore(task=BenchmarkTask.CATEGORIES, score=1.0, details=details)
            return QualityScore(
                task=BenchmarkTask.CATEGORIES,
                score=0.0,
                details={**details, "reason": "unexpected_categories"},
            )

        tp = len(set(actual_norm) & set(expected_norm))
        fp = len(set(actual_norm) - set(expected_norm))
        fn = len(set(expected_norm) - set(actual_norm))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        details["precision"] = round(precision, 4)
        details["recall"] = round(recall, 4)
        details["f1"] = round(f1, 4)

        return QualityScore(task=BenchmarkTask.CATEGORIES, score=round(f1, 4), details=details)

    def _evaluate_companies(self, context: EvaluationContext) -> QualityScore:
        case = context.case
        parsed = context.parsed_structured or {}
        actual_raw = parsed.get("companies", [])
        if actual_raw is None:
            actual_raw = []
        if isinstance(actual_raw, str):
            actual_raw = [actual_raw]

        actual_norm = sorted({_company_norm(c) for c in actual_raw if str(c).strip()})
        expected_norm = sorted({_company_norm(c) for c in case.expected_companies if c.strip()})

        details: dict[str, Any] = {"actual": actual_norm, "expected": expected_norm}

        if not expected_norm:
            if not actual_norm:
                return QualityScore(task=BenchmarkTask.COMPANIES, score=1.0, details=details)
            return QualityScore(
                task=BenchmarkTask.COMPANIES,
                score=0.0,
                details={**details, "reason": "unexpected_companies"},
            )

        tp = len(set(actual_norm) & set(expected_norm))
        fp = len(set(actual_norm) - set(expected_norm))
        fn = len(set(expected_norm) - set(actual_norm))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        details["precision"] = round(precision, 4)
        details["recall"] = round(recall, 4)
        details["f1"] = round(f1, 4)

        return QualityScore(task=BenchmarkTask.COMPANIES, score=round(f1, 4), details=details)

    def _evaluate_topics(self, context: EvaluationContext) -> QualityScore:
        case = context.case
        parsed = context.parsed_structured or {}
        actual_raw = parsed.get("topics", [])
        if actual_raw is None:
            actual_raw = []
        if isinstance(actual_raw, str):
            actual_raw = [actual_raw]

        actual_norm = sorted({_topic_norm(c) for c in actual_raw if str(c).strip()})
        expected_norm = sorted({_topic_norm(c) for c in case.expected_topics if c.strip()})

        details: dict[str, Any] = {"actual": actual_norm, "expected": expected_norm}

        if not expected_norm:
            if not actual_norm:
                return QualityScore(task=BenchmarkTask.TOPICS, score=1.0, details=details)
            return QualityScore(
                task=BenchmarkTask.TOPICS,
                score=0.0,
                details={**details, "reason": "unexpected_topics"},
            )

        tp = len(set(actual_norm) & set(expected_norm))
        fp = len(set(actual_norm) - set(expected_norm))
        fn = len(set(expected_norm) - set(actual_norm))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        details["precision"] = round(precision, 4)
        details["recall"] = round(recall, 4)
        details["f1"] = round(f1, 4)

        return QualityScore(task=BenchmarkTask.TOPICS, score=round(f1, 4), details=details)


def _company_norm(raw: str) -> str:
    cleaned = raw.strip()
    if not cleaned:
        return ""
    return normalize_company(cleaned) or cleaned


def _topic_norm(raw: str) -> str:
    cleaned = raw.strip()
    if not cleaned:
        return ""
    normalized = normalize_topic(cleaned)
    return (normalized or cleaned).lower()


def _dedupe_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _normalized_overlap(a: str, b: str) -> float:
    tokens_a = set(re.findall(r"\w+", a.lower()))
    tokens_b = set(re.findall(r"\w+", b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))


def _overlap_ratio(a: str, b: str) -> float:
    tokens_a = set(re.findall(r"\w+", a.lower()))
    tokens_b = set(re.findall(r"\w+", b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))


def _input_copy_ratio(text: str, source: str) -> float:
    text_tokens = set(re.findall(r"\w+", text.lower()))
    source_tokens = set(re.findall(r"\w+", source.lower()))
    if not text_tokens or not source_tokens:
        return 0.0
    return len(text_tokens & source_tokens) / len(text_tokens)


def evaluate_benchmark_run(run: Any) -> dict[str, Any]:
    """Evaluate all results in a benchmark run and return summary statistics."""
    from ai_news_digest.application.ai.benchmark.models import (
        BenchmarkRun,
        TaskScore,
    )

    if not isinstance(run, BenchmarkRun):
        raise TypeError("run must be a BenchmarkRun.")

    task_scores: dict[str, list[float]] = {}
    task_counts: dict[str, int] = {}

    for result in run.results:
        if result.quality_score is not None:
            key = result.quality_score.task.value
            task_scores.setdefault(key, []).append(result.quality_score.score)
            task_counts[key] = task_counts.get(key, 0) + 1

    aggregated: dict[str, TaskScore] = {}
    for key, scores in task_scores.items():
        aggregated[key] = TaskScore(
            task=BenchmarkTask(key),
            cases_evaluated=len(scores),
            cases_passed=sum(1 for s in scores if s >= 0.5),
            cases_failed=sum(1 for s in scores if s < 0.5),
            total_score=sum(scores),
            max_possible_score=len(scores),
            mean_score=sum(scores) / len(scores) if scores else 0.0,
            min_score=min(scores) if scores else 0.0,
            max_score=max(scores) if scores else 0.0,
        )

    return {"task_scores": aggregated}


__all__ = [
    "BenchmarkEvaluator",
    "EvaluationContext",
    "evaluate_benchmark_run",
]
