"""Unit tests for ``SemanticCandidateFinder``."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ai_news_digest.application.services.semantic_candidate_finder import (
    SemanticCandidateFinder,
)
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_cluster import StoryCluster


def make_article(**overrides):
    defaults = {
        "title": "OpenAI announces GPT-5 model",
        "category_id": None,
        "company_ids": set(),
        "topic_ids": set(),
        "published_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    article = Article.create(
        title=defaults.pop("title"),
        url=f"https://example.com/{uuid4()}",
        summary="A summary for testing.",
        content="Article body content.",
        source_id=uuid4(),
        published_at=defaults.pop("published_at"),
    )
    article.category_id = defaults.pop("category_id")
    article.company_ids = defaults.pop("company_ids")
    article.topic_ids = defaults.pop("topic_ids")
    for key, value in defaults.items():
        setattr(article, key, value)
    return article


def make_cluster(**overrides):
    cluster = StoryCluster.create(
        title="AI Model Announcements",
        slug="ai-model-announcements",
        summary="Cluster about AI models.",
    )
    for key, value in overrides.items():
        setattr(cluster, key, value)
    return cluster


@pytest.fixture
def mock_repositories():
    article_repository = AsyncMock()
    cluster_repository = AsyncMock()
    return article_repository, cluster_repository


@pytest.mark.asyncio
async def test_find_candidates_returns_clusters_and_articles(mock_repositories):
    article_repository, cluster_repository = mock_repositories

    cluster = make_cluster()
    article = make_article()
    cluster_repository.find_recent_active_clusters.return_value = [cluster]
    article_repository.find_recent_candidate_articles.return_value = [article]

    finder = SemanticCandidateFinder(
        article_repository=article_repository,
        cluster_repository=cluster_repository,
        time_window_hours=72,
        candidate_limit=50,
    )
    result = await finder.find_candidates(article)

    cluster_repository.find_recent_active_clusters.assert_awaited_once()
    article_repository.find_recent_candidate_articles.assert_awaited_once()

    cluster_kwargs = cluster_repository.find_recent_active_clusters.call_args.kwargs
    article_kwargs = article_repository.find_recent_candidate_articles.call_args.kwargs

    assert cluster_kwargs["category_id"] is None
    assert cluster_kwargs["company_ids"] == []
    assert cluster_kwargs["topic_ids"] == []
    assert "announces" in cluster_kwargs["title_tokens"]
    assert cluster_kwargs["limit"] == 50

    assert article_kwargs["category_id"] is None
    assert article_kwargs["company_ids"] == []
    assert article_kwargs["topic_ids"] == []
    assert "announces" in article_kwargs["title_tokens"]
    assert article_kwargs["limit"] == 50
    assert article_kwargs["exclude_article_id"] == article.id

    assert result == ([cluster], [article])
    assert result == ([cluster], [article])


@pytest.mark.asyncio
async def test_candidate_limit_truncates(mock_repositories):
    article_repository, cluster_repository = mock_repositories

    clusters = [make_cluster() for _ in range(30)]
    articles = [make_article() for _ in range(30)]
    cluster_repository.find_recent_active_clusters.return_value = clusters
    article_repository.find_recent_candidate_articles.return_value = articles

    finder = SemanticCandidateFinder(
        article_repository=article_repository,
        cluster_repository=cluster_repository,
        time_window_hours=72,
        candidate_limit=20,
    )
    result = await finder.find_candidates(make_article())

    assert len(result[0]) == 10
    assert len(result[1]) == 10


@pytest.mark.asyncio
async def test_passes_article_filters_to_repositories(mock_repositories):
    article_repository, cluster_repository = mock_repositories

    article = make_article(
        title="OpenAI GPT-5 announcement",
        category_id="cat-1",
        company_ids={"openai"},
        topic_ids={"ai-models"},
    )
    cluster_repository.find_recent_active_clusters.return_value = []
    article_repository.find_recent_candidate_articles.return_value = []

    finder = SemanticCandidateFinder(
        article_repository=article_repository,
        cluster_repository=cluster_repository,
        time_window_hours=24,
        candidate_limit=10,
    )
    await finder.find_candidates(article)

    call_kwargs = cluster_repository.find_recent_active_clusters.call_args.kwargs
    assert call_kwargs["category_id"] == "cat-1"
    assert call_kwargs["company_ids"] == ["openai"]
    assert call_kwargs["topic_ids"] == ["ai-models"]
    assert "openai" in call_kwargs["title_tokens"]
    assert "gpt5" in call_kwargs["title_tokens"]
