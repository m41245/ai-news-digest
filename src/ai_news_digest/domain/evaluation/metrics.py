from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class EvaluationMetricType(StrEnum):
    STRUCTURED_OUTPUT_VALIDITY = "structured_output_validity"
    SUMMARY_PRESENCE = "summary_presence"
    SUMMARY_LENGTH_BOUNDS = "summary_length_bounds"
    SUMMARY_EMPTY_RATE = "summary_empty_rate"
    SUMMARY_OVERSIZED_RATE = "summary_oversized_rate"
    SUMMARY_INPUT_COPY_RATE = "summary_input_copy_rate"
    TAKEAWAY_COUNT = "takeaway_count"
    TAKEAWAY_DUPLICATE_RATE = "takeaway_duplicate_rate"
    TAKEAWAY_EMPTY_RATE = "takeaway_empty_rate"
    CATEGORY_VALIDITY = "category_validity"
    COMPANY_NORMALIZATION = "company_normalization"
    TOPIC_NORMALIZATION = "topic_normalization"
    WHY_IT_MATTERS_PRESENCE = "why_it_matters_presence"
    METADATA_COMPLETENESS = "metadata_completeness"
    CLAIM_COMPLETENESS = "claim_completeness"
    EVIDENCE_ATTACHMENT_RATE = "evidence_attachment_rate"
    SUPPORTED_CLAIM_RATE = "supported_claim_rate"
    EVIDENCE_COVERAGE = "evidence_coverage"
    CONFLICT_DETECTION_RATE = "conflict_detection_rate"
    CLUSTER_DUPLICATE_RATE = "cluster_duplicate_rate"
    CLUSTER_SINGLETON_RATE = "cluster_singleton_rate"
    RANKING_STABILITY = "ranking_stability"
    ACTIVITY_CLASSIFICATION_STABILITY = "activity_classification_stability"
    TREND_SCORE_DISTRIBUTION = "trend_score_distribution"
    PREFERENCE_ALIGNMENT = "preference_alignment"
    MUTE_COMPLIANCE = "mute_compliance"
    RECOMMENDATION_DIVERSITY = "recommendation_diversity"
    SEMANTIC_RESULT_VALIDITY = "semantic_result_validity"
    GRAPH_RELATIONSHIP_COMPLETENESS = "graph_relationship_completeness"
    PROVENANCE_COMPLETENESS = "provenance_completeness"
    EXPLANATION_COVERAGE = "explanation_coverage"
    EXTRACTION_SUCCESS_RATE = "extraction_success_rate"
    EXTRACTION_FALLBACK_RATE = "extraction_fallback_rate"
    PROVIDER_VALIDITY = "provider_validity"
    PROVIDER_LATENCY = "provider_latency"
    PROVIDER_TOKEN_USAGE = "provider_token_usage"  # noqa: S105
    PROVIDER_COST = "provider_cost"
    OVERALL_QUALITY = "overall_quality"


class EvaluationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DriftState(StrEnum):
    STABLE = "stable"
    WATCH = "watch"
    DRIFTED = "drifted"


@dataclass(slots=True)
class MetricValue:
    metric_type: EvaluationMetricType
    value: float
    sample_count: int = 0
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    schema_version: str = "v1"
    dataset_version: str = ""
    benchmark_version: str = "m93-v1"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationResult:
    run_id: str
    metric_type: EvaluationMetricType
    value: float
    sample_count: int = 0
    scope: str = ""
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    schema_version: str = "v1"
    dataset_version: str = ""
    benchmark_version: str = "m93-v1"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QualitySnapshot:
    snapshot_id: str
    evaluated_at: datetime
    scope: str
    metrics: list[MetricValue]
    sample_count: int = 0
    provider: str | None = None
    model: str | None = None
    dataset_version: str = ""
    benchmark_version: str = "m93-v1"
    configuration_version: str = ""


@dataclass(slots=True)
class DriftSignal:
    metric_type: EvaluationMetricType
    baseline_value: float | None
    current_value: float
    difference: float
    relative_change: float
    threshold: float
    state: DriftState
    baseline_sample_count: int = 0
    current_sample_count: int = 0
    scope: str = ""
    provider: str | None = None
    model: str | None = None


@dataclass(slots=True)
class EvaluationReport:
    run_id: str
    started_at: datetime
    completed_at: datetime | None
    status: EvaluationStatus
    evaluation_type: str
    scope: str
    dataset_version: str
    benchmark_version: str
    configuration_version: str
    metrics: list[MetricValue]
    sample_count: int
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    schema_version: str = "v1"
    drift_signals: list[DriftSignal] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "DriftSignal",
    "DriftState",
    "EvaluationMetricType",
    "EvaluationReport",
    "EvaluationResult",
    "EvaluationStatus",
    "MetricValue",
    "QualitySnapshot",
]
