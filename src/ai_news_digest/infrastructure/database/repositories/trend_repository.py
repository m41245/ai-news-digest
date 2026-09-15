from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.models.trend import Trend
from ai_news_digest.domain.ports.trend_repository import TrendRepository
from ai_news_digest.infrastructure.database.mappers.trend_mapper import TrendMapper, _serialize_metadata
from ai_news_digest.infrastructure.database.models.trend_model import TrendModel
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class SqlAlchemyTrendRepository(BaseRepository[TrendModel], TrendRepository):
    """
    SQLAlchemy implementation of the TrendRepository port.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, trend: Trend) -> Trend:
        model = TrendMapper.to_model(trend)
        model = await self._add_and_refresh(model)
        return TrendMapper.to_domain(model)

    async def get_by_id(self, trend_id: UUID) -> Trend | None:
        statement = select(TrendModel).where(TrendModel.id == str(trend_id))
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return TrendMapper.to_domain(model)

    async def get_by_canonical_key(self, canonical_key: str) -> Trend | None:
        statement = select(TrendModel).where(TrendModel.canonical_key == canonical_key)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return TrendMapper.to_domain(model)

    async def list_public(
        self,
        *,
        trend_type: str | None = None,
        status: str | None = None,
        min_score: float | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Trend]:
        statement = select(TrendModel).order_by(TrendModel.trend_score.desc())

        if trend_type is not None:
            statement = statement.where(TrendModel.trend_type == trend_type)

        if status is not None:
            statement = statement.where(TrendModel.status == status)

        if min_score is not None:
            statement = statement.where(TrendModel.trend_score >= min_score)

        statement = statement.limit(limit).offset(offset)
        result = await self._session.execute(statement)
        return [TrendMapper.to_domain(model) for model in result.scalars().all()]

    async def count_public(
        self,
        *,
        trend_type: str | None = None,
        status: str | None = None,
        min_score: float | None = None,
    ) -> int:
        statement = select(func.count()).select_from(TrendModel)

        if trend_type is not None:
            statement = statement.where(TrendModel.trend_type == trend_type)

        if status is not None:
            statement = statement.where(TrendModel.status == status)

        if min_score is not None:
            statement = statement.where(TrendModel.trend_score >= min_score)

        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def upsert(self, trend: Trend) -> Trend:
        existing = await self.get_by_canonical_key(trend.canonical_key)
        if existing is None:
            return await self.create(trend)

        statement = (
            update(TrendModel)
            .where(TrendModel.canonical_key == trend.canonical_key)
            .values(
                trend_type=trend.trend_type.value,
                display_name=trend.display_name,
                status=trend.status.value,
                trend_score=trend.trend_score,
                momentum_score=trend.momentum_score,
                last_detected_at=trend.last_detected_at,
                recent_activity=trend.recent_activity,
                baseline_activity=trend.baseline_activity,
                source_count=trend.source_count,
                story_count=trend.story_count,
                event_count=trend.event_count,
                explanation=trend.explanation,
                trend_metadata=_serialize_metadata(trend.trend_metadata),
                updated_at=datetime.now(UTC),
            )
        )
        await self._session.execute(statement)
        await self._commit()
        updated = await self.get_by_canonical_key(trend.canonical_key)
        return updated if updated is not None else trend

    async def list_recent(
        self,
        *,
        since: datetime,
        limit: int = 100,
    ) -> list[Trend]:
        statement = (
            select(TrendModel)
            .where(TrendModel.last_detected_at >= since)
            .order_by(TrendModel.last_detected_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return [TrendMapper.to_domain(model) for model in result.scalars().all()]


__all__ = ["SqlAlchemyTrendRepository"]
