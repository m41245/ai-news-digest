from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

    from ai_news_digest.domain.models.trend import Trend


class TrendRepository(ABC):
    """
    Port for persisting and retrieving trends.
    """

    @abstractmethod
    async def create(self, trend: Trend) -> Trend:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, trend_id: UUID) -> Trend | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_canonical_key(self, canonical_key: str) -> Trend | None:
        raise NotImplementedError

    @abstractmethod
    async def list_public(
        self,
        *,
        trend_type: str | None = None,
        status: str | None = None,
        min_score: float | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Trend]:
        raise NotImplementedError

    @abstractmethod
    async def count_public(
        self,
        *,
        trend_type: str | None = None,
        status: str | None = None,
        min_score: float | None = None,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def upsert(self, trend: Trend) -> Trend:
        raise NotImplementedError

    @abstractmethod
    async def list_recent(
        self,
        *,
        since: datetime,
        limit: int = 100,
    ) -> list[Trend]:
        raise NotImplementedError

    @abstractmethod
    async def list_personalized(
        self,
        *,
        user_preference_profile: Any,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Trend]:
        raise NotImplementedError


__all__ = ["TrendRepository"]
