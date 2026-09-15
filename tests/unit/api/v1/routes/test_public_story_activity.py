"""
Unit tests for M83 story activity public API responses.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.public import router
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.cluster_status import ClusterStatus
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.enums.story_activity_status import StoryActivityStatus
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.story_activity import StoryActivity
from ai_news_digest.domain.models.story_cluster import StoryCluster


def _make_source(
    source_id: uuid4,
    name: str,
    is_active: bool = True,
    status: SourceStatus = SourceStatus.VERIFIED,
    source_type: SourceType = SourceType.TECH_PUBLICATION,
) -> Source:
    return Source(
        id=source_id,
        name=name,
        feed_url=f"https://example.com/feed/{source_id}",
        website_url=f"https://example.com/{source_id}",
        description=f"Source {name}",
        is_active=is_active,
        source_type=source_type,
        status=status,
        created_at=datetime.now(UTC),
    )


def _make_article(
    article_id: uuid4,
    cluster_id: uuid4,
    source_id: uuid4,
    published_at: datetime,
    status: ArticleStatus = ArticleStatus.READY,
) -> Article:
    article = Article.create(
        title=f"Article {article_id}",
        url=f"https://example.com/article/{article_id}",
        summary=f"Summary for article {article_id}",
        content=f"Content for article {article_id}",
        source_id=source_id,
        published_at=published_at,
    )
    article.id = article_id
    article.cluster_id = cluster_id
    article.status = status
    return article


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    container.story_cluster_repository = AsyncMock()
    container.article_repository = AsyncMock()
    container.source_repository = AsyncMock()
    container.claim_repository = AsyncMock()
    container.conflict_repository = AsyncMock()
    container.story_activity_repository = AsyncMock()
    container.category_repository = AsyncMock()
    container.company_repository = AsyncMock()
    container.topic_repository = AsyncMock()
    container.digest_repository = AsyncMock()
    return container


@pytest.fixture
def client(mock_container: MagicMock) -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: mock_container
    from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        yield test_client


class TestPublicStoryClusterActivity:
    def test_story_cluster_includes_activity_status(
        self,
        client: TestClient,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        now = datetime.now(UTC)
        cluster = StoryCluster(
            id=cluster_id,
            title="Test Story",
            slug="test-story",
            summary="A test story",
            first_published_at=now,
            last_updated_at=now,
            status=ClusterStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = []
        mock_container.source_repository.list_all.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None

        response = client.get(f"/public/story-clusters/{cluster.slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["activity_status"] is None
        assert data["activity_score"] is None

    def test_story_cluster_with_activity(
        self,
        client: TestClient,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        now = datetime.now(UTC)
        cluster = StoryCluster(
            id=cluster_id,
            title="Test Story",
            slug="test-story",
            summary="A test story",
            first_published_at=now,
            last_updated_at=now,
            status=ClusterStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        activity = StoryActivity.create(
            story_cluster_id=cluster_id,
            status=StoryActivityStatus.BREAKING,
            activity_score=0.9,
            confidence=0.8,
            explanation="High velocity",
            evaluated_at=now,
            detection_version="v1",
        )
        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = []
        mock_container.source_repository.list_all.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = activity

        response = client.get(f"/public/story-clusters/{cluster.slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["activity_status"] == "breaking"
        assert data["activity_score"] == 0.9
        assert data["latest_activity_at"] == now.isoformat()


__all__ = ["TestPublicStoryClusterActivity"]
