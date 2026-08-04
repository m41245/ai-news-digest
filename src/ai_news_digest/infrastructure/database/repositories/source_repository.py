from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.ports.source_repository import (
    SourceRepository as SourceRepositoryPort,
)
from ai_news_digest.infrastructure.database.mappers.source_mapper import (
    SourceMapper,
)
from ai_news_digest.infrastructure.database.models.source_model import (
    SourceModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class SourceRepository(
    BaseRepository[SourceModel],
    SourceRepositoryPort,
):
    """
    SQLAlchemy implementation of the SourceRepository port.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        super().__init__(session)

    async def create(
        self,
        source: Source,
    ) -> Source:
        """
        Persist a new source.
        """
        model = SourceMapper.to_model(source)
        model = await self._add_and_refresh(model)
        return SourceMapper.to_domain(model)

    async def get_by_id(
        self,
        source_id: UUID,
    ) -> Source | None:
        """
        Retrieve a source by its identifier.
        """
        statement = select(SourceModel).where(SourceModel.id == str(source_id))

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return None

        return SourceMapper.to_domain(model)

    async def get_by_feed_url(
        self,
        feed_url: str,
    ) -> Source | None:
        """
        Retrieve a source by its RSS feed URL.
        """
        statement = select(SourceModel).where(SourceModel.feed_url == feed_url)

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return None

        return SourceMapper.to_domain(model)

    async def list_all(self) -> list[Source]:
        """
        Return all configured news sources ordered by name.
        """
        statement = select(SourceModel).order_by(SourceModel.name.asc())

        result = await self._session.execute(statement)

        models = result.scalars().all()

        return [SourceMapper.to_domain(model) for model in models]

    async def list_enabled(self) -> list[Source]:
        """
        Return all enabled news sources.
        """
        statement = (
            select(SourceModel)
            .where(SourceModel.is_active.is_(True))
            .order_by(SourceModel.name.asc())
        )

        result = await self._session.execute(statement)

        models = result.scalars().all()

        return [SourceMapper.to_domain(model) for model in models]

    async def list_active(self) -> list[Source]:
        """
        Compatibility alias for the ingestion service.
        """
        return await self.list_enabled()

    async def update(
        self,
        source: Source,
    ) -> Source:
        """
        Update an existing source.
        """
        statement = select(SourceModel).where(SourceModel.id == str(source.id))

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            raise ValueError(f"Source with id '{source.id}' was not found.")

        SourceMapper.update_model(
            model,
            source,
        )

        await self._commit()

        model = await self._refresh(model)

        return SourceMapper.to_domain(model)

    async def delete(
        self,
        source_id: UUID,
    ) -> None:
        """
        Delete a source by its identifier.
        """
        statement = select(SourceModel).where(SourceModel.id == str(source_id))

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return

        await self._delete(model)
