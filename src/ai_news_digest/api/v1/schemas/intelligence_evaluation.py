from __future__ import annotations

from pydantic import BaseModel


class EvaluationRunResponse(BaseModel):
    run_id: str
    evaluation_type: str
    scope: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    dataset_version: str = "production"
    benchmark_version: str = "m93-v1"
    configuration_version: str = "v1"
    provider: str | None = None
    model: str | None = None
    sample_count: int = 0
    metric_count: int = 0
    error: str | None = None


class EvaluationMetricResponse(BaseModel):
    metric_type: str
    value: float
    sample_count: int = 0
    scope: str = ""
    provider: str | None = None
    model: str | None = None


class EvaluationDetailResponse(BaseModel):
    run: EvaluationRunResponse
    metrics: list[EvaluationMetricResponse]


class DriftSignalResponse(BaseModel):
    metric_type: str
    baseline_value: float | None
    current_value: float
    difference: float
    relative_change: float
    threshold: float
    state: str
    scope: str = ""
    provider: str | None = None
    model: str | None = None


class QualitySnapshotResponse(BaseModel):
    snapshot_id: str
    evaluated_at: str | None = None
    scope: str
    sample_count: int = 0
    overall_quality: float | None = None
    structured_output_validity: float | None = None
    summary_presence: float | None = None
    provenance_completeness: float | None = None
    evidence_attachment_rate: float | None = None
    extraction_success_rate: float | None = None


class TriggerEvaluationResponse(BaseModel):
    message: str
    run_id: str
    task_id: str | None = None


__all__ = [
    "DriftSignalResponse",
    "EvaluationDetailResponse",
    "EvaluationMetricResponse",
    "EvaluationRunResponse",
    "QualitySnapshotResponse",
    "TriggerEvaluationResponse",
]
