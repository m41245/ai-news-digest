"""
Unit tests for M82 conflict use case.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from ai_news_digest.application.use_cases.claim.detect_conflicts import (
    DetectClaimConflictsUseCase,
)
from ai_news_digest.domain.enums.claim_type import ClaimType
from ai_news_digest.domain.models.claim import Claim
from ai_news_digest.domain.models.conflict import Conflict
from ai_news_digest.domain.ports.claim_repository import ClaimRepository
from ai_news_digest.domain.ports.conflict_repository import ConflictRepository


class MockClaimRepository(ClaimRepository):
    def __init__(
        self,
        claims: list[Claim],
        articles: dict[UUID, Any],
        sources: dict[UUID, Any],
    ) -> None:
        self._claims = claims
        self._articles = articles
        self._sources = sources

    async def create_claim(self, claim: Claim) -> Claim:
        return claim

    async def get_by_id(self, claim_id: UUID) -> Claim | None:
        for c in self._claims:
            if c.id == claim_id:
                return c
        return None

    async def list_by_article_id(self, article_id: UUID) -> list[Claim]:
        return [c for c in self._claims if c.article_id == article_id]

    async def update_claim(self, claim: Claim) -> Claim:
        return claim

    async def delete_claims_for_article(self, article_id: UUID) -> int:
        return 0

    async def create_evidence(self, evidence: Any) -> Any:
        return evidence

    async def list_evidence_by_claim_id(self, claim_id: UUID) -> list[Any]:
        return []

    async def delete_evidence_for_claim(self, claim_id: UUID) -> int:
        return 0

    async def list_recent_for_conflicts(self, *, limit: int = 200) -> list[Claim]:
        return self._claims[:limit]

    async def get_article_for_conflict(self, article_id: UUID) -> Any | None:
        return self._articles.get(article_id)

    async def get_source_for_conflict(self, source_id: UUID) -> Any | None:
        return self._sources.get(source_id)


class MockConflictRepository(ConflictRepository):
    def __init__(self) -> None:
        self._conflicts: dict[str, Conflict] = {}
        self._next_id = 0

    async def create(self, conflict: Conflict) -> Conflict:
        a, b = _canonical_pair(str(conflict.claim_a_id), str(conflict.claim_b_id))
        key = f"{a}:{b}:{conflict.detection_version}"
        if key in self._conflicts:
            return self._conflicts[key]
        self._next_id += 1
        conflict.id = UUID(int=self._next_id)
        self._conflicts[key] = conflict
        return conflict

    async def get_by_id(self, conflict_id: UUID) -> Conflict | None:
        for c in self._conflicts.values():
            if c.id == conflict_id:
                return c
        return None

    async def find_existing(
        self,
        *,
        claim_a_id: UUID,
        claim_b_id: UUID,
        detection_version: str,
    ) -> Conflict | None:
        a, b = _canonical_pair(str(claim_a_id), str(claim_b_id))
        key = f"{a}:{b}:{detection_version}"
        return self._conflicts.get(key)

    async def list_recent(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> list[Conflict]:
        return list(self._conflicts.values())[offset:offset + limit]

    async def list_by_story_cluster_id(
        self, story_cluster_id: UUID, *, limit: int = 50
    ) -> list[Conflict]:
        return [c for c in self._conflicts.values() if c.story_cluster_id == story_cluster_id]

    async def update(self, conflict: Conflict) -> Conflict:
        return conflict

    async def count(self) -> int:
        return len(self._conflicts)


def _canonical_pair(a: str, b: str) -> tuple[str, str]:
    if a <= b:
        return a, b
    return b, a


@pytest.mark.asyncio
async def test_detect_conflicts_creates_conflicts() -> None:
    article_a_id = uuid4()
    article_b_id = uuid4()
    source_a_id = uuid4()
    source_b_id = uuid4()

    article_a = type("Article", (), {
        "id": article_a_id,
        "published_at": datetime.now(UTC),
        "company_ids": ("c1",),
        "topic_ids": ("t1",),
    })()
    article_b = type("Article", (), {
        "id": article_b_id,
        "published_at": datetime.now(UTC),
        "company_ids": ("c1",),
        "topic_ids": ("t1",),
    })()
    source_a = type("Source", (), {"id": source_a_id, "name": "A"})()
    source_b = type("Source", (), {"id": source_b_id, "name": "B"})()

    claim_a = Claim.create(
        article_id=article_a_id,
        source_id=source_a_id,
        claim_text="Model has 70B parameters.",
        claim_type=ClaimType.QUANTITATIVE,
    )
    claim_b = Claim.create(
        article_id=article_b_id,
        source_id=source_b_id,
        claim_text="Model has 120B parameters.",
        claim_type=ClaimType.QUANTITATIVE,
    )

    claim_repo = MockClaimRepository(
        claims=[claim_a, claim_b],
        articles={article_a_id: article_a, article_b_id: article_b},
        sources={source_a_id: source_a, source_b_id: source_b},
    )
    conflict_repo = MockConflictRepository()

    use_case = DetectClaimConflictsUseCase(
        claim_repository=claim_repo,
        conflict_repository=conflict_repo,
        provider_manager=None,
    )
    result = await use_case.execute()
    assert result["conflicts"] >= 1


@pytest.mark.asyncio
async def test_detect_conflicts_prevents_duplicates() -> None:
    article_a_id = uuid4()
    article_b_id = uuid4()
    source_a_id = uuid4()
    source_b_id = uuid4()

    article_a = type("Article", (), {
        "id": article_a_id,
        "published_at": datetime.now(UTC),
        "company_ids": ("c1",),
        "topic_ids": ("t1",),
    })()
    article_b = type("Article", (), {
        "id": article_b_id,
        "published_at": datetime.now(UTC),
        "company_ids": ("c1",),
        "topic_ids": ("t1",),
    })()
    source_a = type("Source", (), {"id": source_a_id, "name": "A"})()
    source_b = type("Source", (), {"id": source_b_id, "name": "B"})()

    claim_a = Claim.create(
        article_id=article_a_id,
        source_id=source_a_id,
        claim_text="Model has 70B parameters.",
        claim_type=ClaimType.QUANTITATIVE,
    )
    claim_b = Claim.create(
        article_id=article_b_id,
        source_id=source_b_id,
        claim_text="Model has 120B parameters.",
        claim_type=ClaimType.QUANTITATIVE,
    )

    claim_repo = MockClaimRepository(
        claims=[claim_a, claim_b],
        articles={article_a_id: article_a, article_b_id: article_b},
        sources={source_a_id: source_a, source_b_id: source_b},
    )
    conflict_repo = MockConflictRepository()

    use_case = DetectClaimConflictsUseCase(
        claim_repository=claim_repo,
        conflict_repository=conflict_repo,
        provider_manager=None,
    )
    result1 = await use_case.execute()
    result2 = await use_case.execute()
    assert result1["conflicts"] >= 1
    assert result2["conflicts"] == 0


__all__ = ["test_detect_conflicts_creates_conflicts", "test_detect_conflicts_prevents_duplicates"]
