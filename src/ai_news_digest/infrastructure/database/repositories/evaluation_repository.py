from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, desc, func, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.evaluation.metrics import EvaluationReport, MetricValue, QualitySnapshot
from ai_news_digest.infrastructure.database.models.evaluation_metric_model import (
    EvaluationMetricModel,
)
from ai_news_digest.infrastructure.database.models.evaluation_run_model import (
    EvaluationRunModel,
)
from ai_news_digest.infrastructure.database.models.quality_snapshot_model import (
    QualitySnapshotModel,
)


class EvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_run(self, report: EvaluationReport) -> EvaluationRunModel:
        model = EvaluationRunModel(
            run_id=report.run_id,
            evaluation_type=report.evaluation_type,
            scope=report.scope,
            status=report.status.value,
            started_at=report.started_at,
            completed_at=report.completed_at,
            dataset_version=report.dataset_version,
            benchmark_version=report.benchmark_version,
            configuration_version=report.configuration_version,
            provider=report.provider,
            model=report.model,
            prompt_version=report.prompt_version,
            schema_version=report.schema_version,
            sample_count=report.sample_count,
            metric_count=len(report.metrics),
            error=report.error,
            extra_metadata=str(report.metadata) if report.metadata else None,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def save_metrics(self, run_id: str, metrics: list[MetricValue]) -> None:
        for m in metrics:
            model = EvaluationMetricModel(
                run_id=run_id,
                metric_type=m.metric_type.value,
                value=m.value,
                sample_count=m.sample_count,
                scope=m.metadata.get("scope", ""),
                provider=m.provider,
                model=m.model,
                prompt_version=m.prompt_version,
                schema_version=m.schema_version,
                dataset_version=m.dataset_version,
                benchmark_version=m.benchmark_version,
                extra_metadata=str(m.metadata) if m.metadata else None,
            )
            self._session.add(model)
        await self._session.flush()

    async def save_snapshot(self, snapshot: QualitySnapshot) -> QualitySnapshotModel:
        metric_map = {m.metric_type.value: m.value for m in snapshot.metrics}
        model = QualitySnapshotModel(
            snapshot_id=snapshot.snapshot_id,
            evaluation_run_id=snapshot.snapshot_id.replace("snap-", ""),
            evaluated_at=snapshot.evaluated_at,
            scope=snapshot.scope,
            sample_count=snapshot.sample_count,
            provider=snapshot.provider,
            model=snapshot.model,
            dataset_version=snapshot.dataset_version,
            benchmark_version=snapshot.benchmark_version,
            configuration_version=snapshot.configuration_version,
            overall_quality=metric_map.get("overall_quality"),
            structured_output_validity=metric_map.get(
                "structured_output_validity"
            ),
            summary_presence=metric_map.get("summary_presence"),
            provenance_completeness=metric_map.get("provenance_completeness"),
            evidence_attachment_rate=metric_map.get("evidence_attachment_rate"),
            extraction_success_rate=metric_map.get("extraction_success_rate"),
            extra_metadata=(
                str({m.metric_type.value: m.value for m in snapshot.metrics})
                if snapshot.metrics
                else None
            ),
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_runs(
        self,
        limit: int = 20,
        offset: int = 0,
        evaluation_type: str | None = None,
        status: str | None = None,
        scope: str | None = None,
        provider: str | None = None,
    ) -> tuple[list[EvaluationRunModel], int]:
        query = select(EvaluationRunModel).order_by(desc(EvaluationRunModel.started_at))
        if evaluation_type:
            query = query.where(EvaluationRunModel.evaluation_type == evaluation_type)
        if status:
            query = query.where(EvaluationRunModel.status == status)
        if scope:
            query = query.where(EvaluationRunModel.scope == scope)
        if provider:
            query = query.where(EvaluationRunModel.provider == provider)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one_or_none() or 0

        query = query.limit(limit).offset(offset)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def get_run(self, run_id: str) -> EvaluationRunModel | None:
        result = await self._session.execute(
            select(EvaluationRunModel).where(EvaluationRunModel.run_id == run_id)
        )
        return result.scalar_one_or_none()

    async def list_metrics(
        self,
        run_id: str,
        metric_type: str | None = None,
    ) -> list[EvaluationMetricModel]:
        query = select(EvaluationMetricModel).where(
            EvaluationMetricModel.run_id == run_id
        )
        if metric_type:
            query = query.where(EvaluationMetricModel.metric_type == metric_type)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_metrics_by_run_id(self, run_id: str) -> list[MetricValue]:
        models = await self.list_metrics(run_id)
        return [
            MetricValue(
                metric_type=EvaluationMetricType(m.metric_type),
                value=m.value,
                sample_count=m.sample_count,
                provider=m.provider,
                model=m.model,
                prompt_version=m.prompt_version,
                schema_version=m.schema_version,
                dataset_version=m.dataset_version,
                benchmark_version=m.benchmark_version,
                metadata={"scope": m.scope},
            )
            for m in models
        ]

    async def get_latest_completed_run(
        self, scope: str, exclude_run_id: str
    ) -> EvaluationRunModel | None:
        result = await self._session.execute(
            select(EvaluationRunModel)
            .where(EvaluationRunModel.scope == scope)
            .where(EvaluationRunModel.status == "completed")
            .where(EvaluationRunModel.run_id != exclude_run_id)
            .order_by(desc(EvaluationRunModel.completed_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_snapshots(
        self,
        limit: int = 30,
        offset: int = 0,
        scope: str | None = None,
    ) -> tuple[list[QualitySnapshotModel], int]:
        query = select(QualitySnapshotModel).order_by(
            desc(QualitySnapshotModel.evaluated_at)
        )
        if scope:
            query = query.where(QualitySnapshotModel.scope == scope)
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one_or_none() or 0
        query = query.limit(limit).offset(offset)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def cleanup_old_runs(self, retention_days: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        stmt = delete(EvaluationRunModel).where(EvaluationRunModel.created_at < cutoff)
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        await self._session.flush()
        return int(result.rowcount)

    async def cleanup_old_snapshots(self, retention_days: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        stmt = delete(QualitySnapshotModel).where(QualitySnapshotModel.created_at < cutoff)
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        await self._session.flush()
        return int(result.rowcount)
