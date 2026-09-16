"""
Unit tests for the M95 Story Intelligence Brief API endpoint.
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
from ai_news_digest.domain.enums.conflict_status import ConflictStatus
from ai_news_digest.domain.enums.conflict_type import ConflictType
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.story_cluster import StoryCluster


def _make_source(
    source_id: uuid4,
    name: str,
    source_type: SourceType = SourceType.TECH_PUBLICATION,
) -> Source:
    return Source(
        id=source_id,
        name=name,
        feed_url=f"https://example.com/feed/{source_id}",
        website_url=f"https://example.com/{source_id}",
        description=f"Source {name}",
        is_active=True,
        source_type=source_type,
        status=SourceStatus.VERIFIED,
        created_at=datetime.now(UTC),
    )


def _make_article(
    article_id: uuid4,
    cluster_id: uuid4,
    source_id: uuid4,
    category_id: uuid4,
    published_at: datetime,
    title: str = "Test Article",
    summary: str = "Test summary",
) -> Article:
    article = Article(
        id=article_id,
        title=title,
        url=f"https://example.com/article/{article_id}",
        summary=summary,
        content="Test content",
        source_id=source_id,
        category_id=category_id,
        published_at=published_at,
        fetched_at=datetime.now(UTC),
        status=ArticleStatus.READY,
    )
    article.cluster_id = cluster_id
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
    container.trend_repository = AsyncMock()
    container.relationship_repository = AsyncMock()
    container.company_repository = AsyncMock()
    container.topic_repository = AsyncMock()
    container.related_story_finder = MagicMock()
    container.quality_gate_repository = AsyncMock()
    container.cache_store = AsyncMock()
    container.cache_store.get.return_value = None
    container.cache_store.set.return_value = None
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


class TestStoryIntelligenceBriefEndpoint:
    def test_brief_returns_200_for_existing_cluster(
        self,
        client: TestClient,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        now = datetime.now(UTC)
        cluster = StoryCluster(
            id=cluster_id,
            title="AI Breakthrough",
            slug="ai-breakthrough",
            summary="A major AI breakthrough was announced.",
            first_published_at=now,
            last_updated_at=now,
            status=ClusterStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        source = _make_source(uuid4(), "Tech Daily")
        category_id = uuid4()
        article = _make_article(
            article_id=uuid4(),
            cluster_id=cluster_id,
            source_id=source.id,
            category_id=category_id,
            published_at=now,
            title="AI Breakthrough",
            summary="A major AI breakthrough was announced.",
        )

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = [article]
        mock_container.source_repository.list_all.return_value = [source]
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        response = client.get(f"/public/story-clusters/{cluster.slug}/brief")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "AI Breakthrough"
        assert data["slug"] == "ai-breakthrough"
        assert data["status"] == "active"
        assert data["article_count"] == 1
        assert data["source_count"] == 1
        assert "summary" in data
        assert "sources" in data
        assert "claims" in data
        assert "conflicts" in data
        assert "timeline" in data
        assert "story_evolution" in data
        assert "trends" in data
        assert "entities" in data
        assert "related_stories" in data
        assert "provenance" in data
        assert "quality" in data
        assert "updated_at" in data

    def test_brief_returns_404_for_missing_cluster(
        self,
        client: TestClient,
        mock_container: MagicMock,
    ) -> None:
        mock_container.story_cluster_repository.get_by_slug.return_value = None
        response = client.get("/public/story-clusters/nonexistent-story/brief")
        assert response.status_code == 404

    def test_brief_includes_key_takeaways(
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
            summary="Test summary",
            first_published_at=now,
            last_updated_at=now,
            status=ClusterStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        source = _make_source(uuid4(), "Tech Daily")
        category_id = uuid4()
        article = _make_article(
            article_id=uuid4(),
            cluster_id=cluster_id,
            source_id=source.id,
            category_id=category_id,
            published_at=now,
            summary="Test summary",
        )
        article.key_takeaways = ["Takeaway 1", "Takeaway 2"]

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = [article]
        mock_container.source_repository.list_all.return_value = [source]
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        response = client.get(f"/public/story-clusters/{cluster.slug}/brief")
        assert response.status_code == 200
        data = response.json()
        assert "Takeaway 1" in data["key_takeaways"]
        assert "Takeaway 2" in data["key_takeaways"]

    def test_brief_includes_conflicts(
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
            summary="Test summary",
            first_published_at=now,
            last_updated_at=now,
            status=ClusterStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        source_a = _make_source(uuid4(), "Source A", SourceType.TECH_PUBLICATION)
        source_b = _make_source(uuid4(), "Source B", SourceType.BUSINESS_NEWS)
        category_id_a = uuid4()
        category_id_b = uuid4()
        article_a = _make_article(
            article_id=uuid4(),
            cluster_id=cluster_id,
            source_id=source_a.id,
            category_id=category_id_a,
            published_at=now,
            title="Article A",
        )
        article_b = _make_article(
            article_id=uuid4(),
            cluster_id=cluster_id,
            source_id=source_b.id,
            category_id=category_id_b,
            published_at=now,
            title="Article B",
        )

        from ai_news_digest.domain.models.conflict import Conflict

        conflict = Conflict(
            id=uuid4(),
            claim_a_id=uuid4(),
            claim_b_id=uuid4(),
            article_a_id=article_a.id,
            article_b_id=article_b.id,
            source_a_id=source_a.id,
            source_b_id=source_b.id,
            conflict_type=ConflictType.OTHER,
            status=ConflictStatus.CONFIRMED,
            confidence=0.8,
            explanation="Sources disagree on the date",
            detection_version="v1",
            story_cluster_id=cluster_id,
            same_source=False,
        )

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = [article_a, article_b]
        mock_container.source_repository.list_all.return_value = [source_a, source_b]
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = [conflict]
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        response = client.get(f"/public/story-clusters/{cluster.slug}/brief")
        assert response.status_code == 200
        data = response.json()
        assert len(data["conflicts"]) == 1
        assert data["conflicts"][0]["explanation"] == "Sources disagree on the date"

    def test_brief_public_access_requires_no_auth(
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
            summary="Test summary",
            first_published_at=now,
            last_updated_at=now,
            status=ClusterStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = []
        mock_container.source_repository.list_all.return_value = []
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        response = client.get(f"/public/story-clusters/{cluster.slug}/brief")
        assert response.status_code == 200

    def test_brief_returns_degraded_for_single_source(
        self,
        client: TestClient,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        now = datetime.now(UTC)
        cluster = StoryCluster(
            id=cluster_id,
            title="Degraded Story",
            slug="degraded-story",
            summary="Test summary",
            first_published_at=now,
            last_updated_at=now,
            status=ClusterStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        source = _make_source(uuid4(), "Tech Daily")
        category_id = uuid4()
        article = _make_article(
            article_id=uuid4(),
            cluster_id=cluster_id,
            source_id=source.id,
            category_id=category_id,
            published_at=now,
            summary="Test summary",
        )

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = [article]
        mock_container.source_repository.list_all.return_value = [source]
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        response = client.get(f"/public/story-clusters/{cluster.slug}/brief")
        assert response.status_code == 200
        data = response.json()
        assert data["quality"]["health_status"] == "degraded"
        assert data["quality"]["degraded"] is True

    def test_brief_returns_403_for_blocked_quality_gate(
        self,
        client: TestClient,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        now = datetime.now(UTC)
        cluster = StoryCluster(
            id=cluster_id,
            title="Blocked Story",
            slug="blocked-story",
            summary="Test summary",
            first_published_at=now,
            last_updated_at=now,
            status=ClusterStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        source = _make_source(uuid4(), "Tech Daily")
        category_id = uuid4()
        article = _make_article(
            article_id=uuid4(),
            cluster_id=cluster_id,
            source_id=source.id,
            category_id=category_id,
            published_at=now,
            summary="Test summary",
        )

        from ai_news_digest.domain.evaluation.quality_gates import (
            IntelligenceComponent,
            QualityGateResultDetail,
        )

        fail_result = QualityGateResultDetail(
            gate_id="story-clustering-success",
            component=IntelligenceComponent.STORY_CLUSTERING,
            metric_type="story_clustering_success_rate",
            result="fail",
            current_value=0.5,
            threshold=0.8,
            operator="gte",
            sample_count=10,
            min_sample_size=5,
            severity="warning",
            explanation="Story clustering success rate below threshold",
            evaluated_at=now,
        )

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = [article]
        mock_container.source_repository.list_all.return_value = [source]
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)
        mock_container.quality_gate_repository.list_results.return_value = ([fail_result], 1)

        response = client.get(f"/public/story-clusters/{cluster.slug}/brief")
        assert response.status_code == 403

    def test_brief_ai_disabled_returns_deterministic_fallback(
        self,
        client: TestClient,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        now = datetime.now(UTC)
        cluster = StoryCluster(
            id=cluster_id,
            title="AI Disabled Story",
            slug="ai-disabled-story",
            summary=None,
            first_published_at=now,
            last_updated_at=now,
            status=ClusterStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = []
        mock_container.source_repository.list_all.return_value = []
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        response = client.get(f"/public/story-clusters/{cluster.slug}/brief")
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] is None
        assert data["key_takeaways"] == []
        assert data["why_it_matters"] is None
        assert data["quality"]["health_status"] == "insufficient_data"


__all__ = ["TestStoryIntelligenceBriefEndpoint"]
