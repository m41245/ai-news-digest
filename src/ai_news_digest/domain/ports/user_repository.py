from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from ai_news_digest.domain.models.user import User


class UserRepository(ABC):
    """Port for persisting and retrieving users."""

    @abstractmethod
    async def create(
        self,
        user: User,
    ) -> User:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_email(
        self,
        email: str,
    ) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def list_all(
        self,
    ) -> list[User]:
        """Return all users ordered by creation time (oldest first)."""
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        user: User,
    ) -> User:
        """Persist changes to an existing user."""
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        user_id: UUID,
    ) -> None:
        """Delete a user by identifier."""
        raise NotImplementedError
