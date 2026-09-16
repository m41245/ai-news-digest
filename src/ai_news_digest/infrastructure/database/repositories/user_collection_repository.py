from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.core.exceptions import DatabaseError
from ai_news_digest.domain.models.user_collection import UserCollection
from ai_news_digest.domain.ports.user_collection_repository import (
    UserCollectionRepository as UserCollectionRepositoryPort,
)
from ai_news_digest.infrastructure.database.models.user_collection_model import (
    UserCollectionModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class SqlAlchemyUserCollectionRepository(
    BaseRepository[UserCollectionModel],
    UserCollectionRepositoryPort,
):
    """SQLAlchemy implementation of the UserCollectionRepository port."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, collection: UserCollection) -> UserCollection:
        model = UserCollectionModel(
            id=str(collection.id),
            user_id=str(collection.user_id),
            name=collection.name,
            description=collection.description,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
        )
        model = await self._add_and_refresh(model)
        return self._to_domain(model)

    async def get_by_id(self, collection_id: UUID) -> UserCollection | None:
        statement = select(UserCollectionModel).where(UserCollectionModel.id == str(collection_id))
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[UserCollection], int]:
        base_statement = select(UserCollectionModel).where(
            UserCollectionModel.user_id == str(user_id),
        ).order_by(UserCollectionModel.updated_at.desc())

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_result = await self._session.execute(count_statement)
        total = total_result.scalar_one()

        statement = base_statement.limit(limit).offset(offset)
        result = await self._session.execute(statement)
        items = [self._to_domain(model) for model in result.scalars().all()]
        return items, total

    async def get_by_user_and_name(
        self,
        user_id: UUID,
        name: str,
    ) -> UserCollection | None:
        statement = select(UserCollectionModel).where(
            UserCollectionModel.user_id == str(user_id),
            UserCollectionModel.name == name,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def update(self, collection: UserCollection) -> UserCollection:
        statement = select(UserCollectionModel).where(UserCollectionModel.id == str(collection.id))
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            raise DatabaseError(f"Collection {collection.id} not found")
        model.name = collection.name
        model.description = collection.description
        model.updated_at = datetime.now(UTC)
        await self._commit()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def delete(self, user_id: UUID, collection_id: UUID) -> bool:
        statement = select(UserCollectionModel).where(
            UserCollectionModel.id == str(collection_id),
            UserCollectionModel.user_id == str(user_id),
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._commit()
        return True

    async def count_by_user(self, user_id: UUID) -> int:
        statement = select(func.count()).select_from(UserCollectionModel).where(
            UserCollectionModel.user_id == str(user_id),
        )
        result = await self._session.execute(statement)
        return result.scalar_one()

    @staticmethod
    def _to_domain(model: UserCollectionModel) -> UserCollection:
        return UserCollection(
            id=UUID(model.id),
            user_id=UUID(model.user_id),
            name=model.name,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
