from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from ai_news_digest.domain.models.conflict import Conflict
from ai_news_digest.domain.ports.conflict_repository import ConflictRepository
from ai_news_digest.infrastructure.database.mappers.conflict_mapper import ConflictMapper
from ai_news_digest.infrastructure.database.models.conflict_model import (
    ConflictModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class SqlAlchemyConflictRepository(BaseRepository[ConflictModel], ConflictRepository):
    """
    SQLAlchemy implementation of the ConflictRepository port.
    """

    def __init__(self, session: Any) -> None:
        super().__init__(session)

    async def create(self, conflict: Conflict) -> Conflict:
        model = ConflictMapper.to_model(conflict)
        model = await self._add_and_refresh(model)
        return ConflictMapper.to_domain(model)

    async def get_by_id(self, conflict_id: UUID) -> Conflict | None:
        statement = select(ConflictModel).where(
            ConflictModel.id == str(conflict_id)
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return ConflictMapper.to_domain(model)

    async def find_existing(
        self,
        *,
        claim_a_id: UUID,
        claim_b_id: UUID,
        detection_version: str,
    ) -> Conflict | None:
        a, b = _canonical_pair(str(claim_a_id), str(claim_b_id))
        statement = select(ConflictModel).where(
            ConflictModel.claim_a_id == a,
            ConflictModel.claim_b_id == b,
            ConflictModel.detection_version == detection_version,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return ConflictMapper.to_domain(model)

    async def list_recent(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> list[Conflict]:
        statement = select(ConflictModel).order_by(
            ConflictModel.created_at.desc()
        ).limit(limit).offset(offset)
        if status is not None:
            statement = statement.where(ConflictModel.status == status)
        result = await self._session.execute(statement)
        return [ConflictMapper.to_domain(model) for model in result.scalars().all()]

    async def list_by_story_cluster_id(
        self,
        story_cluster_id: UUID,
        *,
        limit: int = 50,
    ) -> list[Conflict]:
        statement = (
            select(ConflictModel)
            .where(ConflictModel.story_cluster_id == str(story_cluster_id))
            .order_by(ConflictModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return [ConflictMapper.to_domain(model) for model in result.scalars().all()]

    async def update(self, conflict: Conflict) -> Conflict:
        statement = select(ConflictModel).where(
            ConflictModel.id == str(conflict.id)
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Conflict with id '{conflict.id}' was not found.")
        ConflictMapper.update_model(model, conflict)
        await self._commit()
        model = await self._refresh(model)
        return ConflictMapper.to_domain(model)

    async def count(self) -> int:
        statement = select(func.count()).select_from(ConflictModel)
        result = await self._session.execute(statement)
        return int(result.scalar_one())


def _canonical_pair(a: str, b: str) -> tuple[str, str]:
    """Return (min, max) ordered pair for deduplication."""
    if a <= b:
        return a, b
    return b, a


__all__ = ["SqlAlchemyConflictRepository"]
