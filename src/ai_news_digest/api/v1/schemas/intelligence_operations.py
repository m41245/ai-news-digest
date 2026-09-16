from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class QualityGateResultResponse(BaseModel):
    gate_id: str
    component: str
    metric_type: str
    result: str
    current_value: float | None = None
    threshold: float
    operator: str
    sample_count: int = 0
    min_sample_size: int = 0
    severity: str
    explanation: str | None = None
    evaluated_at: str | None = None
    evaluation_run_id: str | None = None


class ComponentHealthResponse(BaseModel):
    component: str
    status: str
    metric_type: str | None = None
    metric_value: float | None = None
    sample_count: int = 0
    baseline_value: float | None = None
    drift_state: str | None = None
    last_evaluation_at: str | None = None
    evaluation_run_id: str | None = None
    warnings: list[str] = []
    gate_results: list[QualityGateResultResponse] = []


class IntelligenceHealthResponse(BaseModel):
    overall_status: str
    components: list[ComponentHealthResponse]
    generated_at: str | None = None
    evaluation_run_id: str | None = None
    scope: str = "global"
    warnings: list[str] = []


class OperationalAlertResponse(BaseModel):
    alert_id: str
    severity: str
    component: str
    gate_id: str | None = None
    message: str
    details: dict[str, Any] | None = None
    resolved: bool = False
    resolved_at: str | None = None
    created_at: str | None = None


class TriggerQualityGateEvaluationResponse(BaseModel):
    message: str
    run_id: str
    task_id: str | None = None


class QualityGateDefinitionResponse(BaseModel):
    gate_id: str
    component: str
    metric_type: str
    operator: str
    threshold: float
    min_sample_size: int = 0
    severity: str
    enabled: bool = True
    description: str | None = None
    version: str = "v1"


__all__ = [
    "ComponentHealthResponse",
    "IntelligenceHealthResponse",
    "OperationalAlertResponse",
    "QualityGateDefinitionResponse",
    "QualityGateResultResponse",
    "TriggerQualityGateEvaluationResponse",
]
