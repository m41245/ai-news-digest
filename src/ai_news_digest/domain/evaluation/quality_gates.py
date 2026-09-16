from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class QualityGateResult(StrEnum):
    """Deterministic quality gate outcomes."""

    PASS = "pass"  # noqa: S105
    WARN = "warn"
    FAIL = "fail"
    INSUFFICIENT_DATA = "insufficient_data"


class IntelligenceHealthStatus(StrEnum):
    """Component-level intelligence health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    INSUFFICIENT_DATA = "insufficient_data"
    UNKNOWN = "unknown"


class AlertSeverity(StrEnum):
    """Operational alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class IntelligenceComponent(StrEnum):
    """Measurable intelligence components."""

    EXTRACTION = "extraction"
    ARTICLE_ANALYSIS = "article_analysis"
    CLAIMS_EVIDENCE = "claims_evidence"
    CONFLICT_DETECTION = "conflict_detection"
    STORY_CLUSTERING = "story_clustering"
    STORY_ACTIVITY = "story_activity"
    STORY_EVENTS = "story_events"
    TRENDS = "trends"
    RANKING = "ranking"
    RECOMMENDATIONS = "recommendations"
    SEMANTIC_SEARCH = "semantic_search"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    TEMPORAL_GRAPH = "temporal_graph"
    DIGEST_GENERATION = "digest_generation"
    PROVIDER_HEALTH = "provider_health"
    OVERALL = "overall"


class GateOperator(StrEnum):
    """Comparison operators for quality gates."""

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NEQ = "neq"


@dataclass(slots=True)
class QualityGate:
    """Configurable quality gate definition."""

    gate_id: str
    component: IntelligenceComponent
    metric_type: str
    operator: GateOperator
    threshold: float
    min_sample_size: int = 0
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True
    description: str = ""
    version: str = "v1"


@dataclass(slots=True)
class QualityGateResultDetail:
    """Result of evaluating a single quality gate."""

    gate_id: str
    component: IntelligenceComponent
    metric_type: str
    result: QualityGateResult
    current_value: float | None
    threshold: float
    operator: GateOperator
    sample_count: int
    min_sample_size: int
    severity: AlertSeverity
    explanation: str
    evaluated_at: datetime
    evaluation_run_id: str | None = None
    configuration_version: str = "v1"


@dataclass(slots=True)
class ComponentHealth:
    """Health status for a single intelligence component."""

    component: IntelligenceComponent
    status: IntelligenceHealthStatus
    gate_results: list[QualityGateResultDetail] = field(default_factory=list)
    metric_value: float | None = None
    metric_type: str | None = None
    sample_count: int = 0
    baseline_value: float | None = None
    drift_state: str | None = None
    last_evaluation_at: datetime | None = None
    evaluation_run_id: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IntelligenceHealthReport:
    """Aggregated intelligence health report."""

    overall_status: IntelligenceHealthStatus
    components: list[ComponentHealth]
    generated_at: datetime
    evaluation_run_id: str | None = None
    scope: str = "global"
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OperationalAlert:
    """Persisted operational alert."""

    alert_id: str
    severity: AlertSeverity
    component: IntelligenceComponent
    gate_id: str | None
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deduplication_key: str = ""


@dataclass(slots=True)
class AlertDeduplicationWindow:
    """Configuration for alert deduplication."""

    deduplication_window_seconds: int = 3600
    deduplication_key_prefix: str = "intelligence-alert"


__all__ = [
    "AlertDeduplicationWindow",
    "AlertSeverity",
    "ComponentHealth",
    "GateOperator",
    "IntelligenceComponent",
    "IntelligenceHealthReport",
    "IntelligenceHealthStatus",
    "OperationalAlert",
    "QualityGate",
    "QualityGateResult",
    "QualityGateResultDetail",
]
