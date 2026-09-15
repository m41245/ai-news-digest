"""Unit tests for RelatedStoryFinder."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_news_digest.application.ai.embedding_service import EmbeddingService
from ai_news_digest.application.ai.semantic_search_service import SemanticSearchService
from ai_news_digest.application.services.related_story_finder import (
    RelatedStoryFinder,
)
from ai_news_digest.application.services.semantic_candidate_finder import (
    SemanticCandidateFinder,
)
from ai_news_digest.application.services.semantic_duplicate_detector import (
    SemanticDuplicateDetector,
    SemanticMatchResult,
)
from ai_news_digest.domain.enums.semantic_match_type import SemanticMatchType
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
    article.cluster_id = None
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
    service.generate = AsyncMock(
        return_value=MagicMock(embedding=(1.0, 0.0, 0.0))
    )
    return service


@pytest.fixture
def mock_semantic_search() -> SemanticSearchService:
    search = MagicMock(spec=SemanticSearchService)

    async def _search_clusters(query, clusters, query_embedding=None):
        return [
            MagicMock(
                cluster=c,
                similarity=0.8,
                article_count=3,
                source_count=2,
            )
            for c in clusters
        ]

    search.search_clusters = AsyncMock(side_effect=_search_clusters)
    search.search_articles = AsyncMock(return_value=[])
    return search


@pytest.fixture
def mock_duplicate_detector() -> SemanticDuplicateDetector:
    detector = MagicMock(spec=SemanticDuplicateDetector)
    detector.compare_with_cluster = AsyncMock(
        return_value=MagicMock(
            match_type=SemanticMatchType.RELATED_BUT_DISTINCT,
            signals=("shared_topic:1",),
        )
    )
    return detector


@pytest.fixture
def mock_candidate_finder() -> MagicMock:
    return MagicMock(spec=SemanticCandidateFinder)


@pytest.fixture
def finder(
    mock_embedding_service: EmbeddingService,
    mock_semantic_search: SemanticSearchService,
    mock_duplicate_detector: SemanticDuplicateDetector,
    mock_candidate_finder: MagicMock,
) -> RelatedStoryFinder:
    return RelatedStoryFinder(
        embedding_service=mock_embedding_service,
        semantic_search=mock_semantic_search,
        duplicate_detector=mock_duplicate_detector,
        candidate_finder=mock_candidate_finder,
    )


class TestRelatedStoryFinder:
    @pytest.mark.asyncio
    async def test_empty_clusters_returns_empty(self, finder: RelatedStoryFinder) -> None:
        result = await finder.find_for_article(
            _make_article(), None, [], limit=10
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_excludes_current_cluster(
        self, finder: RelatedStoryFinder
    ) -> None:
        cluster = _make_cluster("Current")
        article = _make_article("Test")
        article.cluster_id = cluster.id
        result = await finder.find_for_article(
            article, str(cluster.id), [cluster], limit=10
        )
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_returns_related_stories(self, finder: RelatedStoryFinder) -> None:
        cluster = _make_cluster("Related")
        article = _make_article("Test")
        result = await finder.find_for_article(
            article, None, [cluster], limit=10
        )
        assert len(result) > 0
        assert result[0].cluster_id == str(cluster.id)

    @pytest.mark.asyncio
    async def test_respects_limit(self, finder: RelatedStoryFinder) -> None:
        clusters = [_make_cluster(f"Cluster {i}") for i in range(20)]
        article = _make_article("Test")
        result = await finder.find_for_article(
            article, None, clusters, limit=5
        )
        assert len(result) <= 5
