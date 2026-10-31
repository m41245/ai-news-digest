"""Unit tests for SemanticSearchService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_news_digest.application.ai.embedding_service import EmbeddingService
from ai_news_digest.application.ai.semantic_search_service import (
    ScoredArticle,
    ScoredCluster,
    SemanticSearchService,
)
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_cluster import StoryCluster


def _make_article(title: str = "Test Article") -> Article:
    import uuid

    from ai_news_digest.domain.enums.article_status import ArticleStatus

    article = Article.create(
        title=title,
        url=f"https://example.com/{uuid.uuid4()}",
        summary="Test summary",
        content=None,
        source_id=uuid.uuid4(),
        published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    )
    article.status = ArticleStatus.READY
    article.importance_score = 0.8
    return article


def _make_cluster(title: str = "Test Cluster") -> StoryCluster:
    return StoryCluster.create(
        title=title,
        slug="test-cluster",
        first_published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    )


@pytest.fixture
def mock_embedding_service() -> EmbeddingService:
    service = MagicMock(spec=EmbeddingService)
    service.is_available = True
    service.generate_batch = AsyncMock(
        return_value=MagicMock(
            results=[
                MagicMock(embedding=(1.0, 0.0, 0.0)),
                MagicMock(embedding=(0.0, 1.0, 0.0)),
            ]
        )
    )
    return service


class TestSemanticSearchService:
    @pytest.mark.asyncio
    async def test_empty_candidates_returns_empty(
        self, mock_embedding_service: EmbeddingService
    ) -> None:
        svc = SemanticSearchService(embedding_service=mock_embedding_service)
        result = await svc.search_articles("query", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_fallback_when_no_embedding_provider(self) -> None:
        service = MagicMock(spec=EmbeddingService)
        service.is_available = False
        svc = SemanticSearchService(embedding_service=service)
        articles = [_make_article("A"), _make_article("B")]
        result = await svc.search_articles("query", articles)
        assert len(result) == 2
        assert all(r.similarity == 0.0 for r in result)

    @pytest.mark.asyncio
    async def test_returns_scored_articles(self, mock_embedding_service: EmbeddingService) -> None:
        svc = SemanticSearchService(embedding_service=mock_embedding_service)
        articles = [_make_article("A"), _make_article("B")]
        result = await svc.search_articles("query", articles, query_embedding=(1.0, 0.0, 0.0))
        assert len(result) == 2
        assert all(isinstance(r, ScoredArticle) for r in result)
        assert all(0.0 <= r.similarity <= 1.0 for r in result)

    @pytest.mark.asyncio
    async def test_search_clusters_empty(self, mock_embedding_service: EmbeddingService) -> None:
        svc = SemanticSearchService(embedding_service=mock_embedding_service)
        result = await svc.search_clusters("query", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_search_clusters_returns_scored(
        self, mock_embedding_service: EmbeddingService
    ) -> None:
        svc = SemanticSearchService(embedding_service=mock_embedding_service)
        clusters = [_make_cluster("C1"), _make_cluster("C2")]
        result = await svc.search_clusters("query", clusters, query_embedding=(1.0, 0.0, 0.0))
        assert len(result) == 2
        assert all(isinstance(r, ScoredCluster) for r in result)

    @pytest.mark.asyncio
    async def test_duplicate_article_ids_are_deduplicated(self) -> None:
        from uuid import uuid4

        # Use real service with unavailable embedding to exercise fallback ordering.
        embedding = MagicMock(spec=EmbeddingService)
        embedding.is_available = False
        svc = SemanticSearchService(embedding_service=embedding)

        shared_id = uuid4()
        a1 = _make_article("A")
        a2 = _make_article("B")
        a1.id = shared_id
        a2.id = shared_id
        result = await svc.search_articles("query", [a2, a1])
        assert len(result) == 1
        assert result[0].article.id == shared_id

    @pytest.mark.asyncio
    async def test_equal_scores_use_article_id_tiebreaker(self) -> None:
        from uuid import UUID

        embedding = MagicMock(spec=EmbeddingService)
        embedding.is_available = True
        # Return identical embeddings so scores tie.
        embedding.generate_batch = AsyncMock(
            return_value=MagicMock(
                results=[
                    MagicMock(embedding=(1.0, 0.0, 0.0)),
                    MagicMock(embedding=(1.0, 0.0, 0.0)),
                ]
            )
        )
        svc = SemanticSearchService(embedding_service=embedding)
        a1 = _make_article("A")
        a2 = _make_article("B")
        # Force deterministic ids for tie-break assertion.
        a1.id = UUID("00000000-0000-0000-0000-000000000002")
        a2.id = UUID("00000000-0000-0000-0000-000000000001")
        result = await svc.search_articles("query", [a1, a2], query_embedding=(1.0, 0.0, 0.0))
        assert len(result) == 2
        # Equal combined scores: lower article id first.
        assert result[0].article.id == a2.id
        assert result[1].article.id == a1.id

    @pytest.mark.asyncio
    async def test_fallback_path_is_sorted_by_article_id(self) -> None:
        embedding = MagicMock(spec=EmbeddingService)
        embedding.is_available = False
        svc = SemanticSearchService(embedding_service=embedding)
        a1 = _make_article("A")
        a2 = _make_article("B")
        result = await svc.search_articles("query", [a1, a2])
        ids = [r.article.id for r in result]
        assert ids == sorted(ids)

    @pytest.mark.asyncio
    async def test_empty_candidates_returns_empty_fallback(self) -> None:
        embedding = MagicMock(spec=EmbeddingService)
        embedding.is_available = True
        svc = SemanticSearchService(embedding_service=embedding)
        result = await svc.search_articles("query", [])
        assert result == []
