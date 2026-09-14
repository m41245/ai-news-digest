"""
Core benchmark domain models for M80.

These models are provider-neutral and do not reference any specific
AI provider implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class FailureCategory(StrEnum):
    """Classification of benchmark failures."""

    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    UNAVAILABLE = "unavailable"
    INVALID_RESPONSE = "invalid_response"
    SCHEMA_VALIDATION = "schema_validation"
    UNKNOWN_PROVIDER_ERROR = "unknown_provider_error"


class BenchmarkTask(StrEnum):
    """Supported benchmark task types."""

    SUMMARY = "summary"
    KEY_TAKEAWAYS = "key_takeaways"
    WHY_IT_MATTERS = "why_it_matters"
    CATEGORIES = "categories"
    COMPANIES = "companies"
    TOPICS = "topics"
    STRUCTURED_OUTPUT_VALIDITY = "structured_output_validity"


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """A single deterministic benchmark case.

    Contains an input article and expected characteristics used to
    evaluate one or more AI tasks.
    """

    case_id: str
    task: BenchmarkTask
    article_title: str
    article_content: str
    expected_categories: tuple[str, ...] = ()
    expected_companies: tuple[str, ...] = ()
    expected_topics: tuple[str, ...] = ()
    reference_summary: str | None = None
    reference_key_takeaways: tuple[str, ...] = ()
    reference_why_it_matters: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("case_id must not be empty.")
        if not self.article_title.strip():
            raise ValueError("article_title must not be empty.")
        if not self.article_content.strip():
            raise ValueError("article_content must not be empty.")


@dataclass(frozen=True, slots=True)
class QualityScore:
    """Normalized score for a single task dimension.

    Uses a 0-1 scale where 1.0 is perfect.
    """

    task: BenchmarkTask
    score: float
    max_score: float = 1.0
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_score <= 0:
            raise ValueError("max_score must be > 0.")
        bounded = max(0.0, min(self.max_score, self.score))
        object.__setattr__(self, "score", bounded)


@dataclass(slots=True)
class TaskScore:
    """Aggregated scores for a single task across all evaluated cases."""

    task: BenchmarkTask
    cases_evaluated: int = 0
    cases_passed: int = 0
    cases_failed: int = 0
    total_score: float = 0.0
    max_possible_score: float = 0.0
    mean_score: float = 0.0
    min_score: float = 0.0
    max_score: float = 0.0

    def __post_init__(self) -> None:
        if self.cases_evaluated < 0:
            raise ValueError("cases_evaluated must be >= 0.")
        if self.cases_passed < 0:
            raise ValueError("cases_passed must be >= 0.")
        if self.cases_failed < 0:
            raise ValueError("cases_failed must be >= 0.")
        if self.cases_passed + self.cases_failed > self.cases_evaluated:
            raise ValueError("passed + failed must not exceed evaluated.")


@dataclass(frozen=True, slots=True)
class OverallQualityScore:
    """Overall quality score combining task-level scores."""

    tasks: tuple[TaskScore, ...] = ()
    overall_score: float = 0.0
    overall_max: float = 0.0
    overall_mean: float = 0.0
    weighting: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.overall_score < 0.0:
            raise ValueError("overall_score must be >= 0.")
        if self.overall_max <= 0:
            raise ValueError("overall_max must be > 0.")
        bounded = max(0.0, min(self.overall_max, self.overall_score))
        object.__setattr__(self, "overall_score", bounded)


@dataclass(slots=True)
class BenchmarkFailureInfo:
    """Details about a single benchmark failure."""

    provider_id: str
    model: str
    case_id: str
    task: BenchmarkTask
    category: FailureCategory
    error_message: str
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class BenchmarkResult:
    """Result for a single provider/model on a single benchmark case."""

    provider_id: str
    model: str
    case_id: str
    task: BenchmarkTask
    quality_score: QualityScore | None = None
    failure: BenchmarkFailureInfo | None = None
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    cost_known: bool = False
    usage_known: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BenchmarkRun:
    """Complete benchmark run across providers, models, cases, and tasks."""

    run_id: str
    dataset_version: str
    benchmark_version: str
    started_at: datetime
    completed_at: datetime | None = None
    config: dict[str, Any] = field(default_factory=dict)
    results: list[BenchmarkResult] = field(default_factory=list)
    provider_ids: tuple[str, ...] = ()
    model_ids: tuple[str, ...] = ()
    case_ids: tuple[str, ...] = ()
    task_ids: tuple[str, ...] = ()
    total_requests: int = 0
    successes: int = 0
    failures: int = 0
    overall_score: OverallQualityScore | None = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must not be empty.")


@dataclass(frozen=True, slots=True)
class BenchmarkComparison:
    """Pairwise or multi-provider comparison data."""

    provider_id: str
    model: str
    overall_quality: float
    structured_validity: float
    summary_score: float
    takeaways_score: float
    why_it_matters_score: float
    category_f1: float
    company_f1: float
    topic_f1: float
    success_rate: float
    median_latency_ms: float | None
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost: float
    cost_known: bool
    cases_evaluated: int = 0


@dataclass(frozen=True, slots=True)
class BenchmarkDataset:
    """Collection of benchmark cases."""

    name: str
    version: str
    cases: tuple[BenchmarkCase, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty.")
        if not self.version:
            raise ValueError("version must not be empty.")


__all__ = [
    "BenchmarkCase",
    "BenchmarkComparison",
    "BenchmarkDataset",
    "BenchmarkFailureInfo",
    "BenchmarkResult",
    "BenchmarkRun",
    "BenchmarkTask",
    "FailureCategory",
    "OverallQualityScore",
    "QualityScore",
    "TaskScore",
]
