from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from ai_news_digest.domain.models.article import Article
    from ai_news_digest.domain.models.claim import Claim
    from ai_news_digest.domain.models.evidence import Evidence
    from ai_news_digest.domain.models.source import Source


class ClaimRepository(ABC):
    """Port for persisting and retrieving claims and evidence."""

    @abstractmethod
    async def create_claim(self, claim: Claim) -> Claim:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, claim_id: UUID) -> Claim | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_article_id(self, article_id: UUID) -> list[Claim]:
        raise NotImplementedError

    @abstractmethod
    async def update_claim(self, claim: Claim) -> Claim:
        raise NotImplementedError

    @abstractmethod
    async def delete_claims_for_article(self, article_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    async def create_evidence(self, evidence: Evidence) -> Evidence:
        raise NotImplementedError

    @abstractmethod
    async def list_evidence_by_claim_id(self, claim_id: UUID) -> list[Evidence]:
        raise NotImplementedError

    @abstractmethod
    async def delete_evidence_for_claim(self, claim_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    async def list_recent_for_conflicts(
        self,
        *,
        limit: int = 200,
    ) -> list[Claim]:
        """Return recent claims eligible for conflict detection."""
        raise NotImplementedError

    @abstractmethod
    async def get_article_for_conflict(self, article_id: UUID) -> Article | None:
        """Return an article for conflict candidate enrichment."""
        raise NotImplementedError

    @abstractmethod
    async def get_source_for_conflict(self, source_id: UUID) -> Source | None:
        """Return a source for conflict candidate enrichment."""
        raise NotImplementedError
