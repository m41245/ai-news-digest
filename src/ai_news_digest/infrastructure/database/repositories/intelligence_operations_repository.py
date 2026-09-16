from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import delete, desc, func, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.evaluation.quality_gates import (
    ComponentHealth,
    QualityGateResultDetail,
)
from ai_news_digest.infrastructure.database.models.component_health_snapshot_model import (
    ComponentHealthSnapshotModel,
)
from ai_news_digest.infrastructure.database.models.operational_alert_model import (
    OperationalAlertModel,
)
from ai_news_digest.infrastructure.database.models.quality_gate_result_model import (
    QualityGateResultModel,
)


class QualityGateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_result(self, result: QualityGateResultDetail) -> QualityGateResultModel:
        model = QualityGateResultModel(
            gate_id=result.gate_id,
            component=result.component.value,
            metric_type=result.metric_type,
            result=result.result.value,
            current_value=result.current_value,
            threshold=result.threshold,
            operator=result.operator.value,
            sample_count=result.sample_count,
            min_sample_size=result.min_sample_size,
            severity=result.severity.value,
            explanation=result.explanation,
            evaluation_run_id=result.evaluation_run_id,
            configuration_version=result.configuration_version,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_results(
        self,
        limit: int = 50,
        offset: int = 0,
        component: str | None = None,
        result: str | None = None,
        evaluation_run_id: str | None = None,
    ) -> tuple[list[QualityGateResultModel], int]:
        query = select(QualityGateResultModel).order_by(
            desc(QualityGateResultModel.created_at)
        )
        if component:
            query = query.where(QualityGateResultModel.component == component)
        if result:
            query = query.where(QualityGateResultModel.result == result)
        if evaluation_run_id:
            query = query.where(
                QualityGateResultModel.evaluation_run_id == evaluation_run_id
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one_or_none() or 0
        query = query.limit(limit).offset(offset)
        result_rows = await self._session.execute(query)
        return list(result_rows.scalars().all()), total

    async def cleanup_old_results(self, retention_days: int) -> int:
        cutoff = datetime.now(UTC) - __import__("datetime").timedelta(days=retention_days)
        stmt = delete(QualityGateResultModel).where(
            QualityGateResultModel.created_at < cutoff
        )
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        await self._session.flush()
        return int(result.rowcount)


class OperationalAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_alert(self, alert: Any) -> OperationalAlertModel:
        model = OperationalAlertModel(
            alert_id=alert.alert_id,
            severity=alert.severity.value,
            component=alert.component.value,
            gate_id=alert.gate_id,
            message=alert.message,
            details=str(alert.details) if alert.details else None,
            resolved=1 if alert.resolved else 0,
            resolved_at=alert.resolved_at,
            deduplication_key=alert.deduplication_key,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_alerts(
        self,
        limit: int = 50,
        offset: int = 0,
        component: str | None = None,
        severity: str | None = None,
        resolved: bool | None = None,
    ) -> tuple[list[OperationalAlertModel], int]:
        query = select(OperationalAlertModel).order_by(
            desc(OperationalAlertModel.created_at)
        )
        if component:
            query = query.where(OperationalAlertModel.component == component)
        if severity:
            query = query.where(OperationalAlertModel.severity == severity)
        if resolved is not None:
            query = query.where(
                OperationalAlertModel.resolved == (1 if resolved else 0)
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one_or_none() or 0
        query = query.limit(limit).offset(offset)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def find_alert_by_deduplication_key(
        self, deduplication_key: str
    ) -> OperationalAlertModel | None:
        result = await self._session.execute(
            select(OperationalAlertModel).where(
                OperationalAlertModel.deduplication_key == deduplication_key
            )
        )
        return result.scalar_one_or_none()

    async def resolve_alert(self, alert_id: str) -> OperationalAlertModel | None:
        result = await self._session.execute(
            select(OperationalAlertModel).where(
                OperationalAlertModel.alert_id == alert_id
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.resolved = True
        model.resolved_at = datetime.now(UTC)
        await self._session.flush()
        return model

    async def cleanup_old_alerts(self, retention_days: int) -> int:
        cutoff = datetime.now(UTC) - __import__("datetime").timedelta(days=retention_days)
        stmt = delete(OperationalAlertModel).where(
            OperationalAlertModel.created_at < cutoff
        )
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        await self._session.flush()
        return int(result.rowcount)


class ComponentHealthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_snapshot(self, health: ComponentHealth) -> ComponentHealthSnapshotModel:
        model = ComponentHealthSnapshotModel(
            snapshot_id=(
                f"health-{health.component.value}-"
                f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
            ),
            component=health.component.value,
            status=health.status.value,
            metric_type=health.metric_type,
            metric_value=health.metric_value,
            sample_count=health.sample_count,
            baseline_value=health.baseline_value,
            drift_state=health.drift_state,
            evaluation_run_id=health.evaluation_run_id,
            configuration_version="v1",
            warnings="; ".join(health.warnings) if health.warnings else None,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_snapshots(
        self,
        limit: int = 50,
        offset: int = 0,
        component: str | None = None,
    ) -> tuple[list[ComponentHealthSnapshotModel], int]:
        query = select(ComponentHealthSnapshotModel).order_by(
            desc(ComponentHealthSnapshotModel.created_at)
        )
        if component:
            query = query.where(ComponentHealthSnapshotModel.component == component)
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one_or_none() or 0
        query = query.limit(limit).offset(offset)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def cleanup_old_snapshots(self, retention_days: int) -> int:
        cutoff = datetime.now(UTC) - __import__("datetime").timedelta(days=retention_days)
        stmt = delete(ComponentHealthSnapshotModel).where(
            ComponentHealthSnapshotModel.created_at < cutoff
        )
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        await self._session.flush()
        return int(result.rowcount)


__all__ = [
    "ComponentHealthRepository",
    "OperationalAlertRepository",
    "QualityGateRepository",
]
