"""
API routes for M94 intelligence operations, quality gates, and alerts.

Provides authenticated admin endpoints for operational health,
quality gates, and alert management.
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
from ai_news_digest.api.v1.schemas.intelligence_operations import (
    ComponentHealthResponse,
    IntelligenceHealthResponse,
    OperationalAlertResponse,
    QualityGateDefinitionResponse,
    QualityGateResultResponse,
    TriggerQualityGateEvaluationResponse,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.evaluation.quality_gates import (
    ComponentHealth,
    IntelligenceComponent,
    IntelligenceHealthStatus,
)
from ai_news_digest.domain.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/intelligence",
    tags=["Intelligence Operations"],
)


def _gate_result_to_response(model: Any) -> QualityGateResultResponse:
    return QualityGateResultResponse(
        gate_id=model.gate_id,
        component=model.component,
        metric_type=model.metric_type,
        result=model.result,
        current_value=model.current_value,
        threshold=model.threshold,
        operator=model.operator,
        sample_count=model.sample_count,
        min_sample_size=model.min_sample_size,
        severity=model.severity,
        explanation=model.explanation,
        evaluated_at=model.created_at.isoformat() if model.created_at else None,
        evaluation_run_id=model.evaluation_run_id,
    )


def _alert_to_response(model: Any) -> OperationalAlertResponse:
    return OperationalAlertResponse(
        alert_id=model.alert_id,
        severity=model.severity,
        component=model.component,
        gate_id=model.gate_id,
        message=model.message,
        details=None,
        resolved=bool(model.resolved),
        resolved_at=model.resolved_at.isoformat() if model.resolved_at else None,
        created_at=model.created_at.isoformat() if model.created_at else None,
    )


@router.get(
    "/health",
    response_model=IntelligenceHealthResponse,
    summary="Get intelligence health status",
)
async def get_intelligence_health(
    container: Annotated[Container, Depends(get_container)],
    __admin_user: Annotated[User, Depends(get_current_admin_user)],
    scope: str = Query(default="global", max_length=128),
) -> IntelligenceHealthResponse:
    """Return overall intelligence health and component breakdowns (admin only)."""
    from ai_news_digest.application.services.intelligence_health_service import (
        IntelligenceHealthService,
    )
    from ai_news_digest.infrastructure.database.repositories.intelligence_operations_repository import (  # noqa: E501
        ComponentHealthRepository,
    )

    health_service = IntelligenceHealthService()
    component_health_repo = ComponentHealthRepository(container.session)

    snapshots, _ = await component_health_repo.list_snapshots(limit=100)
    if not snapshots:
        return IntelligenceHealthResponse(
            overall_status="unknown",
            components=[],
            generated_at=None,
            warnings=["No health snapshots available"],
        )

    latest_snapshot = snapshots[0]
    components_by_name: dict[str, Any] = {}
    for snap in snapshots:
        name = snap.component
        if name not in components_by_name:
            components_by_name[name] = snap

    component_responses: list[ComponentHealthResponse] = []
    for comp_name, snap in components_by_name.items():
        try:
            IntelligenceComponent(comp_name)
        except ValueError:
            continue
        component_responses.append(
            ComponentHealthResponse(
                component=comp_name,
                status=snap.status,
                metric_type=snap.metric_type,
                metric_value=snap.metric_value,
                sample_count=snap.sample_count,
                baseline_value=snap.baseline_value,
                drift_state=snap.drift_state,
                last_evaluation_at=(
                    snap.created_at.isoformat() if snap.created_at else None
                ),
                evaluation_run_id=snap.evaluation_run_id,
                warnings=snap.warnings.split("; ") if snap.warnings else [],
            )
        )

    overall = health_service.aggregate_overall_health(
        [
            ComponentHealth(
                component=IntelligenceComponent(c.component),
                status=IntelligenceHealthStatus(c.status),
                metric_value=c.metric_value,
                sample_count=c.sample_count,
                warnings=c.warnings,
            )
            for c in component_responses
        ]
    )

    return IntelligenceHealthResponse(
        overall_status=overall.overall_status.value,
        components=component_responses,
        generated_at=overall.generated_at.isoformat(),
        evaluation_run_id=latest_snapshot.evaluation_run_id,
        scope=scope,
        warnings=overall.warnings,
    )


@router.get(
    "/gates",
    response_model=PaginatedResponse[QualityGateResultResponse],
    summary="List quality gate results",
)
async def list_quality_gate_results(
    container: Annotated[Container, Depends(get_container)],
    __admin_user: Annotated[User, Depends(get_current_admin_user)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
    component: str | None = Query(default=None),
    result: str | None = Query(default=None),
) -> PaginatedResponse[QualityGateResultResponse]:
    """List bounded quality gate results (admin only)."""
    from ai_news_digest.infrastructure.database.repositories.intelligence_operations_repository import (  # noqa: E501
        QualityGateRepository,
    )

    repo = QualityGateRepository(container.session)
    models, total = await repo.list_results(
        limit=limit, offset=offset, component=component, result=result
    )
    return PaginatedResponse(
        items=[_gate_result_to_response(m) for m in models],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/gates/definitions",
    response_model=list[QualityGateDefinitionResponse],
    summary="List active quality gate definitions",
)
async def list_quality_gate_definitions(
    __admin_user: Annotated[User, Depends(get_current_admin_user)],
) -> list[QualityGateDefinitionResponse]:
    """Return active quality gate definitions (admin only)."""
    from ai_news_digest.application.services.quality_gate_service import QualityGateService

    service = QualityGateService()
    gates = service.default_gates()
    return [
        QualityGateDefinitionResponse(
            gate_id=g.gate_id,
            component=g.component.value,
            metric_type=g.metric_type,
            operator=g.operator.value,
            threshold=g.threshold,
            min_sample_size=g.min_sample_size,
            severity=g.severity.value,
            enabled=g.enabled,
            description=g.description,
            version=g.version,
        )
        for g in gates
    ]


@router.get(
    "/alerts",
    response_model=PaginatedResponse[OperationalAlertResponse],
    summary="List operational alerts",
)
async def list_operational_alerts(
    container: Annotated[Container, Depends(get_container)],
    __admin_user: Annotated[User, Depends(get_current_admin_user)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
    component: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    resolved: bool | None = Query(default=None),
) -> PaginatedResponse[OperationalAlertResponse]:
    """List bounded operational alerts (admin only)."""
    from ai_news_digest.infrastructure.database.repositories.intelligence_operations_repository import (  # noqa: E501
        OperationalAlertRepository,
    )

    repo = OperationalAlertRepository(container.session)
    models, total = await repo.list_alerts(
        limit=limit, offset=offset, component=component, severity=severity, resolved=resolved
    )
    return PaginatedResponse(
        items=[_alert_to_response(m) for m in models],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=OperationalAlertResponse,
    summary="Resolve an operational alert",
)
async def resolve_operational_alert(
    alert_id: str,
    container: Annotated[Container, Depends(get_container)],
    __admin_user: Annotated[User, Depends(get_current_admin_user)],
) -> OperationalAlertResponse:
    """Resolve a specific operational alert (admin only)."""
    from ai_news_digest.infrastructure.database.repositories.intelligence_operations_repository import (  # noqa: E501
        OperationalAlertRepository,
    )

    repo = OperationalAlertRepository(container.session)
    model = await repo.resolve_alert(alert_id)
    if model is None:
        raise ResourceNotFoundError(f"Alert {alert_id} not found.")
    return _alert_to_response(model)


@router.post(
    "/gates/evaluate",
    response_model=TriggerQualityGateEvaluationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger quality gate evaluation",
)
async def trigger_quality_gate_evaluation(
    __admin_user: Annotated[User, Depends(get_current_admin_user)],
) -> TriggerQualityGateEvaluationResponse:
    """Trigger bounded quality gate evaluation (admin only)."""
    if not get_settings().quality_gates_enabled:
        raise HTTPException(
            status_code=400, detail="Quality gates are disabled by configuration."
        )

    from ai_news_digest.workers.tasks.quality_gates import evaluate_quality_gates

    task = evaluate_quality_gates.delay()
    return TriggerQualityGateEvaluationResponse(
        message="Quality gate evaluation triggered.",
        run_id=f"gate-pending-{task.id}",
        task_id=task.id,
    )


__all__ = ["router"]
