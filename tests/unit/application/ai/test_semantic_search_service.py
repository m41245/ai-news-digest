"""Unit tests for SemanticSearchService."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_news_digest.application.ai.embedding_service import EmbeddingService
from ai_news_digest.application.ai.semantic_search_service import (
    SemanticSearchService,
    ScoredArticle,
    ScoredCluster,
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
    async def test_returns_scored_articles(
        self, mock_embedding_service: EmbeddingService
    ) -> None:
        svc = SemanticSearchService(embedding_service=mock_embedding_service)
        articles = [_make_article("A"), _make_article("B")]
        result = await svc.search_articles(
            "query", articles, query_embedding=(1.0, 0.0, 0.0)
        )
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
        result = await svc.search_clusters(
            "query", clusters, query_embedding=(1.0, 0.0, 0.0)
        )
        assert len(result) == 2
        assert all(isinstance(r, ScoredCluster) for r in result)
