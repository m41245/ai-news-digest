from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ai_news_digest.domain.models.user_preference import UserPreferenceProfile

if TYPE_CHECKING:
    from uuid import UUID


class UserPreferenceRepository(ABC):
    """Port for persisting and retrieving user preference profiles."""

    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
    ) -> UserPreferenceProfile | None:
        raise NotImplementedError

    @abstractmethod
    async def create(
        self,
        profile: UserPreferenceProfile,
    ) -> UserPreferenceProfile:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        profile: UserPreferenceProfile,
    ) -> UserPreferenceProfile:
        raise NotImplementedError

    @abstractmethod
    async def add_followed_company(
        self,
        user_id: UUID,
        company_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def remove_followed_company(
        self,
        user_id: UUID,
        company_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def add_followed_topic(
        self,
        user_id: UUID,
        topic_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def remove_followed_topic(
        self,
        user_id: UUID,
        topic_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def add_followed_category(
        self,
        user_id: UUID,
        category_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def remove_followed_category(
        self,
        user_id: UUID,
        category_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def add_muted_company(
        self,
        user_id: UUID,
        company_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def remove_muted_company(
        self,
        user_id: UUID,
        company_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def add_muted_topic(
        self,
        user_id: UUID,
        topic_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def remove_muted_topic(
        self,
        user_id: UUID,
        topic_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def add_muted_category(
        self,
        user_id: UUID,
        category_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def remove_muted_category(
        self,
        user_id: UUID,
        category_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_user_id(
        self,
        user_id: UUID,
    ) -> None:
        raise NotImplementedError


__all__ = ["UserPreferenceRepository"]
