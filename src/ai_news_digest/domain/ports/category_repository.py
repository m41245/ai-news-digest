from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from ai_news_digest.domain.models.category import Category


class CategoryRepository(ABC):
    """Port for persisting and retrieving categories."""

    @abstractmethod
    async def create(
        self,
        category: Category,
    ) -> Category:
        raise NotImplementedError

    @abstractmethod
    async def create_flush_only(self, category: Category) -> Category:
        """Persist a category without committing the session.

        Mirrors :meth:`create` but leaves transaction control to the caller so
        the category can participate in an outer atomic unit of work.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self,
        category_id: UUID,
    ) -> Category | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_name(
        self,
        name: str,
    ) -> Category | None:
        raise NotImplementedError

    @abstractmethod
    async def list_all(
        self,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Category]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_ids(
        self,
        category_ids: list[UUID],
    ) -> list[Category]:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        category: Category,
    ) -> Category:
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        category_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def count(
        self,
    ) -> int:
        """
        Return the total number of categories.
        """
        raise NotImplementedError
