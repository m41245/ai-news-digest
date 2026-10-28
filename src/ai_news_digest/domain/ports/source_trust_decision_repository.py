from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from ai_news_digest.domain.models.source_trust_decision import SourceTrustDecision


class SourceTrustDecisionRepository(ABC):
    @abstractmethod
    async def create(self, decision: SourceTrustDecision) -> SourceTrustDecision:
        raise NotImplementedError

    @abstractmethod
    async def list_for_source(
        self,
        source_id: UUID,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SourceTrustDecision]:
        raise NotImplementedError

    @abstractmethod
    async def count_for_source(self, source_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        """Roll back the current transaction."""
        raise NotImplementedError
