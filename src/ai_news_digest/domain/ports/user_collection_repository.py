from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ai_news_digest.domain.models.user_collection import UserCollection


class UserCollectionRepository(ABC):
    """Port for persisting and retrieving user collections."""

    @abstractmethod
    async def create(self, collection: UserCollection) -> UserCollection:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, collection_id: UUID) -> UserCollection | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[UserCollection], int]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_and_name(
        self,
        user_id: UUID,
        name: str,
    ) -> UserCollection | None:
        raise NotImplementedError

    @abstractmethod
    async def update(self, collection: UserCollection) -> UserCollection:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, user_id: UUID, collection_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def count_by_user(self, user_id: UUID) -> int:
        raise NotImplementedError
