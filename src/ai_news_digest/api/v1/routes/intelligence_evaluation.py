"""
API routes for M93 intelligence evaluation and drift detection.

Provides authenticated admin endpoints for quality evaluation,
drift detection, and quality snapshots.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ai_news_digest.api.v1.dependencies.auth import get_current_admin_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.common import (
    DEFAULT_PAGE_LIMIT,
    MAX_OFFSET,
    MAX_PAGE_LIMIT,
    PaginatedResponse,
)
from ai_news_digest.api.v1.schemas.intelligence_evaluation import (
    DriftSignalResponse,
    EvaluationDetailResponse,
    EvaluationMetricResponse,
    EvaluationRunResponse,
    QualitySnapshotResponse,
    TriggerEvaluationResponse,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.evaluation.metrics import (
    EvaluationMetricType,
    MetricValue,
)
from ai_news_digest.domain.models.user import User
from ai_news_digest.infrastructure.database.models.evaluation_metric_model import (
    EvaluationMetricModel,
)
from ai_news_digest.infrastructure.database.models.evaluation_run_model import (
    EvaluationRunModel,
)
from ai_news_digest.infrastructure.database.models.quality_snapshot_model import (
    QualitySnapshotModel,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/intelligence",
    tags=["Intelligence Evaluation"],
)


def _run_to_response(model: EvaluationRunModel) -> EvaluationRunResponse:
    return EvaluationRunResponse(
        run_id=model.run_id,
        evaluation_type=model.evaluation_type,
        scope=model.scope,
        status=model.status,
        started_at=model.started_at.isoformat() if model.started_at else None,
        completed_at=model.completed_at.isoformat() if model.completed_at else None,
        dataset_version=model.dataset_version,
        benchmark_version=model.benchmark_version,
        configuration_version=model.configuration_version,
        provider=model.provider,
        model=model.model,
        sample_count=model.sample_count,
        metric_count=model.metric_count,
        error=model.error,
    )


def _metric_to_response(model: EvaluationMetricModel) -> EvaluationMetricResponse:
    return EvaluationMetricResponse(
        metric_type=model.metric_type,
        value=model.value,
        sample_count=model.sample_count,
        scope=model.scope,
        provider=model.provider,
        model=model.model,
    )


def _snapshot_to_response(model: QualitySnapshotModel) -> QualitySnapshotResponse:
    return QualitySnapshotResponse(
        snapshot_id=model.snapshot_id,
        evaluated_at=model.evaluated_at.isoformat() if model.evaluated_at else None,
        scope=model.scope,
        sample_count=model.sample_count,
        overall_quality=model.overall_quality,
        structured_output_validity=model.structured_output_validity,
        summary_presence=model.summary_presence,
        provenance_completeness=model.provenance_completeness,
        evidence_attachment_rate=model.evidence_attachment_rate,
        extraction_success_rate=model.extraction_success_rate,
    )


@router.get(
    "/evaluations",
    response_model=PaginatedResponse[EvaluationRunResponse],
    summary="List evaluation runs",
)
async def list_evaluation_runs(
    container: Annotated[Container, Depends(get_container)],
    __admin_user: Annotated[User, Depends(get_current_admin_user)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
    evaluation_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    provider: str | None = Query(default=None),
) -> PaginatedResponse[EvaluationRunResponse]:
    """List intelligence evaluation runs (admin only)."""
    repo = container.evaluation_repository
    runs, total = await repo.list_runs(
        limit=limit,
        offset=offset,
        evaluation_type=evaluation_type,
        status=status,
        scope=scope,
        provider=provider,
    )
    return PaginatedResponse(
        items=[_run_to_response(r) for r in runs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/evaluations/{run_id}",
    response_model=EvaluationDetailResponse,
    summary="Get evaluation run detail",
)
async def get_evaluation_run(
    run_id: str,
    container: Annotated[Container, Depends(get_container)],
    __admin_user: Annotated[User, Depends(get_current_admin_user)],
) -> EvaluationDetailResponse:
    """Return evaluation run with metrics (admin only)."""
    repo = container.evaluation_repository
    run = await repo.get_run(run_id)
    if run is None:
        raise ResourceNotFoundError(f"Evaluation run {run_id} not found.")
    metrics = await repo.list_metrics(run_id)
    return EvaluationDetailResponse(
        run=_run_to_response(run),
        metrics=[_metric_to_response(m) for m in metrics],
    )


@router.get(
    "/quality/snapshots",
    response_model=PaginatedResponse[QualitySnapshotResponse],
    summary="List quality snapshots",
)
async def list_quality_snapshots(
    container: Annotated[Container, Depends(get_container)],
    __admin_user: Annotated[User, Depends(get_current_admin_user)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
    scope: str | None = Query(default=None),
) -> PaginatedResponse[QualitySnapshotResponse]:
    """List bounded quality snapshots (admin only)."""
    repo = container.evaluation_repository
    snapshots, total = await repo.list_snapshots(limit=limit, offset=offset, scope=scope)
    return PaginatedResponse(
        items=[_snapshot_to_response(s) for s in snapshots],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/evaluations/run",
    response_model=TriggerEvaluationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger an evaluation run",
)
async def trigger_evaluation(
    container: Annotated[Container, Depends(get_container)],
    __admin_user: Annotated[User, Depends(get_current_admin_user)],
    evaluation_type: str = Query(default="manual", pattern="^(manual|daily|benchmark)$"),
    scope: str = Query(default="global", max_length=128),
) -> TriggerEvaluationResponse:
    """Trigger a bounded intelligence evaluation via Celery (admin only)."""
    if not get_settings().evaluation_enabled:
        raise HTTPException(status_code=400, detail="Evaluation is disabled by configuration.")

    from ai_news_digest.workers.tasks.evaluation import run_intelligence_evaluation
    task = run_intelligence_evaluation.delay(evaluation_type=evaluation_type, scope=scope)
    return TriggerEvaluationResponse(
        message="Evaluation triggered.",
        run_id=f"eval-pending-{task.id}",
        task_id=task.id,
    )


@router.get(
    "/drift",
    response_model=list[DriftSignalResponse],
    summary="Get latest drift signals",
)
async def get_drift_signals(
    container: Annotated[Container, Depends(get_container)],
    __admin_user: Annotated[User, Depends(get_current_admin_user)],
    scope: str = Query(default="global", max_length=128),
    provider: str | None = Query(default=None),
) -> list[DriftSignalResponse]:
    """Return drift signals by comparing recent snapshots (admin only)."""
    repo = container.evaluation_repository
    snapshots, _snapshot_total = await repo.list_snapshots(limit=2, scope=scope)
    if len(snapshots) < 2:
        return []

    current_snap = snapshots[0]
    baseline_snap = snapshots[1]

    detector = container.drift_detector
    current_metrics = [
        MetricValue(
            metric_type=EvaluationMetricType(m),
            value=getattr(current_snap, m),
            sample_count=current_snap.sample_count,
        )
        for m in [
            "structured_output_validity",
            "summary_presence",
            "provenance_completeness",
            "evidence_attachment_rate",
            "extraction_success_rate",
            "overall_quality",
        ]
        if getattr(current_snap, m, None) is not None
    ]
    baseline_metrics = [
        MetricValue(
            metric_type=EvaluationMetricType(m),
            value=getattr(baseline_snap, m),
            sample_count=baseline_snap.sample_count,
        )
        for m in [
            "structured_output_validity",
            "summary_presence",
            "provenance_completeness",
            "evidence_attachment_rate",
            "extraction_success_rate",
            "overall_quality",
        ]
        if getattr(baseline_snap, m, None) is not None
    ]

    signals = detector.detect_drift(
        baseline=baseline_metrics,
        current=current_metrics,
        scope=scope,
        provider=provider,
    )
    return [
        DriftSignalResponse(
            metric_type=s.metric_type.value,
            baseline_value=s.baseline_value,
            current_value=s.current_value,
            difference=s.difference,
            relative_change=s.relative_change,
            threshold=s.threshold,
            state=s.state.value,
            scope=s.scope,
            provider=s.provider,
            model=s.model,
        )
        for s in signals
    ]


@router.get(
    "/quality/health",
    summary="Get intelligence quality health status",
)
async def get_quality_health(
    container: Annotated[Container, Depends(get_container)],
    __admin_user: Annotated[User, Depends(get_current_admin_user)],
    scope: str = Query(default="global", max_length=128),
) -> dict[str, Any]:
    """Return bounded quality health status (admin only)."""
    repo = container.evaluation_repository
    snapshots, _snapshot_total = await repo.list_snapshots(limit=1, scope=scope)
    if not snapshots:
        return {"status": "insufficient_data", "warnings": ["No quality snapshots available"]}

    snap = snapshots[0]
    metrics = [
        MetricValue(
            metric_type=EvaluationMetricType(m),
            value=getattr(snap, m),
            sample_count=snap.sample_count,
        )
        for m in [
            "structured_output_validity",
            "summary_presence",
            "provenance_completeness",
            "evidence_attachment_rate",
            "extraction_success_rate",
            "overall_quality",
        ]
        if getattr(snap, m, None) is not None
    ]

    snapshots_for_drift, _drift_total = await repo.list_snapshots(limit=2, scope=scope)
    signals: list[Any] = []
    if len(snapshots_for_drift) >= 2:
        baseline_snap = snapshots_for_drift[1]
        baseline_metrics = [
            MetricValue(
                metric_type=EvaluationMetricType(m),
                value=getattr(baseline_snap, m),
                sample_count=baseline_snap.sample_count,
            )
            for m in [
                "structured_output_validity",
                "summary_presence",
                "provenance_completeness",
                "evidence_attachment_rate",
                "extraction_success_rate",
                "overall_quality",
            ]
            if getattr(baseline_snap, m, None) is not None
        ]
        signals = container.drift_detector.detect_drift(
            baseline=baseline_metrics,
            current=metrics,
            scope=scope,
        )

    status, warnings = container.drift_detector.classify_health(signals, metrics)
    return {
        "status": status,
        "warnings": warnings,
        "sample_count": snap.sample_count,
        "evaluated_at": snap.evaluated_at.isoformat() if snap.evaluated_at else None,
        "overall_quality": snap.overall_quality,
    }


__all__ = ["router"]
