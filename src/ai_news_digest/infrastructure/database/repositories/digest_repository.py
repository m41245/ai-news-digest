from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.domain.ports.digest_repository import (
    DigestRepository as DigestRepositoryPort,
)
from ai_news_digest.infrastructure.database.mappers.digest_mapper import (
    DigestMapper,
)
from ai_news_digest.infrastructure.database.models.digest_article_model import (
    DigestArticleModel,
)
from ai_news_digest.infrastructure.database.models.digest_model import (
    DigestModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class DigestRepository(
    BaseRepository[DigestModel],
    DigestRepositoryPort,
):
    """
    SQLAlchemy implementation of the DigestRepository port.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        super().__init__(session)

    async def create(
        self,
        digest: Digest,
    ) -> Digest:
        """
        Persist a new digest together with its article associations.
        """

        model = DigestMapper.to_model(digest)

        await self._add(model)

        #
        # Flush so the digest exists before inserting
        # digest_article rows.
        #
        await self._flush()

        links = [
            DigestArticleModel(
                digest_id=model.id,
                article_id=str(article_id),
                position=index,
            )
            for index, article_id in enumerate(
                digest.article_ids,
                start=1,
            )
        ]

        if links:
            await self._add_all(links)

        await self._commit()

        await self._refresh(model)

        statement = (
            select(DigestModel)
            .options(
                selectinload(
                    DigestModel.digest_articles,
                )
            )
            .where(
                DigestModel.id == model.id,
            )
        )

        result = await self._session.execute(statement)

        persisted = result.scalar_one()

        return DigestMapper.to_domain(persisted)

    async def get_by_id(
        self,
        digest_id: UUID,
    ) -> Digest | None:
        """
        Retrieve a digest by its identifier.
        """

        statement = (
            select(DigestModel)
            .options(
                selectinload(
                    DigestModel.digest_articles,
                )
            )
            .where(
                DigestModel.id == str(digest_id),
            )
        )

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return None

        return DigestMapper.to_domain(model)

    async def list_recent(
        self,
        limit: int = 30,
        offset: int = 0,
    ) -> list[Digest]:
        """
        Return the most recently generated digests.
        """

        statement = (
            select(DigestModel)
            .options(
                selectinload(
                    DigestModel.digest_articles,
                )
            )
            .order_by(
                DigestModel.generated_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(statement)

        models = result.scalars().all()

        return [DigestMapper.to_domain(model) for model in models]

    async def get_by_title(
        self,
        title: str,
    ) -> Digest | None:
        """
        Return the most recent digest with the given title.
        """

        statement = (
            select(DigestModel)
            .options(
                selectinload(
                    DigestModel.digest_articles,
                )
            )
            .where(
                DigestModel.title == title,
            )
            .order_by(
                DigestModel.generated_at.desc(),
            )
            .limit(1)
        )

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return None

        return DigestMapper.to_domain(model)

    async def update(
        self,
        digest: Digest,
    ) -> Digest:
        """
        Update an existing digest together with its article associations.
        """

        statement = (
            select(DigestModel)
            .options(
                selectinload(
                    DigestModel.digest_articles,
                )
            )
            .where(
                DigestModel.id == str(digest.id),
            )
        )

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            raise ResourceNotFoundError(f"Digest with id '{digest.id}' was not found.")

        DigestMapper.update_model(
            model,
            digest,
        )

        #
        # Remove existing article associations.
        #
        await self._session.execute(
            delete(DigestArticleModel).where(
                DigestArticleModel.digest_id == model.id,
            )
        )

        #
        # Re-create associations from the domain object.
        #
        links = [
            DigestArticleModel(
                digest_id=model.id,
                article_id=str(article_id),
                position=index,
            )
            for index, article_id in enumerate(
                digest.article_ids,
                start=1,
            )
        ]

        if links:
            await self._add_all(links)

        await self._commit()

        statement = (
            select(DigestModel)
            .options(
                selectinload(
                    DigestModel.digest_articles,
                )
            )
            .where(
                DigestModel.id == model.id,
            )
        )

        result = await self._session.execute(statement)

        updated = result.scalar_one()

        return DigestMapper.to_domain(updated)

    async def delete(
        self,
        digest_id: UUID,
    ) -> None:
        """
        Delete a digest and its article associations.
        """

        statement = select(DigestModel).where(
            DigestModel.id == str(digest_id),
        )

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return

        await self._delete(model)

    async def count(self) -> int:
        """Return the total number of digests."""
        statement = select(func.count()).select_from(DigestModel)
        result = await self._session.execute(statement)
        return int(result.scalar_one())
