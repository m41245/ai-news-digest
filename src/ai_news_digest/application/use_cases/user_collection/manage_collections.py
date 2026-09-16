from __future__ import annotations

from uuid import UUID

from ai_news_digest.core.exceptions import DuplicateResourceError, ResourceNotFoundError
from ai_news_digest.domain.models.user_collection import UserCollection
from ai_news_digest.domain.ports.user_collection_repository import UserCollectionRepository


class CreateCollectionUseCase:
    """Use case for creating a user collection."""

    def __init__(self, collection_repository: UserCollectionRepository) -> None:
        self._collection_repository = collection_repository

    async def execute(
        self,
        user_id: UUID,
        name: str,
        description: str | None = None,
    ) -> UserCollection:
        existing = await self._collection_repository.get_by_user_and_name(user_id, name)
        if existing is not None:
            raise DuplicateResourceError(f"Collection '{name}' already exists.")

        collection = UserCollection.create(
            user_id=user_id,
            name=name,
            description=description,
        )
        return await self._collection_repository.create(collection)


class UpdateCollectionUseCase:
    """Use case for updating a user collection."""

    def __init__(self, collection_repository: UserCollectionRepository) -> None:
        self._collection_repository = collection_repository

    async def execute(
        self,
        user_id: UUID,
        collection_id: UUID,
        name: str | None = None,
        description: str | None = None,
    ) -> UserCollection:
        collection = await self._collection_repository.get_by_id(collection_id)
        if collection is None or collection.user_id != user_id:
            raise ResourceNotFoundError("Collection not found.")

        collection.update(name=name, description=description)
        return await self._collection_repository.update(collection)


class DeleteCollectionUseCase:
    """Use case for deleting a user collection."""

    def __init__(self, collection_repository: UserCollectionRepository) -> None:
        self._collection_repository = collection_repository

    async def execute(
        self,
        user_id: UUID,
        collection_id: UUID,
    ) -> None:
        deleted = await self._collection_repository.delete(user_id, collection_id)
        if not deleted:
            raise ResourceNotFoundError("Collection not found.")


class ListCollectionsUseCase:
    """Use case for listing a user's collections."""

    def __init__(self, collection_repository: UserCollectionRepository) -> None:
        self._collection_repository = collection_repository

    async def execute(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[UserCollection], int]:
        return await self._collection_repository.list_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
