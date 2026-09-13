"""
Unit tests for TopStorySelector (M68).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_news_digest.application.services.ranking.story_ranking_service import (
    ClusterRankingContext,
    StoryRankingEngine,
)
from ai_news_digest.application.services.ranking.top_story_selector import (
    TopStorySelector,
    TopStoryResult,
)
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.story_cluster import StoryCluster


def _make_cluster(cluster_id, first_published_at=None):
    return StoryCluster(
        id=cluster_id,
        title="Cluster",
        slug="cluster",
        first_published_at=first_published_at or datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC),
        last_updated_at=datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC),
    )


def _make_article(article_id, source_id, cluster_id=None, published_at=None):
    article_status = __import__(
        "ai_news_digest.domain.enums.article_status", fromlist=["ArticleStatus"]
    ).ArticleStatus.READY
    extraction_method = __import__(
        "ai_news_digest.domain.enums.extraction_method", fromlist=["ExtractionMethod"]
    ).ExtractionMethod.HTML
    return Article(
        id=article_id,
        title=f"Article {article_id}",
        url=f"https://example.com/{article_id}",
        summary="Summary",
        content="Content",
        source_id=source_id,
        category_id=None,
        published_at=published_at or datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC),
        fetched_at=datetime.now(UTC),
        status=article_status,
        extraction_method=extraction_method,
        extraction_quality=__import__(
            "ai_news_digest.domain.enums.extraction_quality", fromlist=["ExtractionQuality"]
        ).ExtractionQuality.FULL,
        company_ids=(),
        topic_ids=(),
        category_ids=(),
        cluster_id=cluster_id,
    )


def _make_source(source_id):
    return Source(
        id=source_id,
        name=f"Source {source_id}",
        feed_url=f"https://example.com/feed/{source_id}",
        website_url=None,
        description=None,
        is_active=True,
        source_type=__import__(
            "ai_news_digest.domain.enums.source_type", fromlist=["SourceType"]
        ).SourceType.TECH_PUBLICATION,
        status=__import__(
            "ai_news_digest.domain.enums.source_status", fromlist=["SourceStatus"]
        ).SourceStatus.VERIFIED,
        created_at=datetime.now(UTC),
    )


def test_empty_candidates_returns_none_top_story():
    selector = TopStorySelector()
    result = selector.select_top_story([])
    assert result.top_story_cluster_id is None
    assert result.top_story_score is None
    assert result.total_candidates == 0


def test_single_candidate_is_top_story():
    engine = StoryRankingEngine()
    selector = TopStorySelector(ranking_engine=engine)
    cluster = _make_cluster(uuid4())
    article = _make_article(uuid4(), uuid4(), cluster_id=cluster.id)
    source = _make_source(article.source_id)
    ctx = ClusterRankingContext(
        cluster=cluster,
        articles=[article],
        source_map={str(source.id): source},
        known_company_ids=set(),
        known_topic_ids=set(),
        known_category_ids=set(),
        now=datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC),
    )
    result = engine.rank_cluster(ctx)
    top_result = selector.select_top_story([result])
    assert top_result.top_story_cluster_id == str(cluster.id)
    assert top_result.top_story_score == result.score


def test_deterministic_tie_breaking():
    engine = StoryRankingEngine()
    selector = TopStorySelector(ranking_engine=engine)
    now = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)
    cluster1 = _make_cluster(uuid4())
    cluster2 = _make_cluster(uuid4())
    article1 = _make_article(uuid4(), uuid4(), cluster_id=cluster1.id)
    article2 = _make_article(uuid4(), uuid4(), cluster_id=cluster2.id)
    source = _make_source(uuid4())
    ctx1 = ClusterRankingContext(
        cluster=cluster1,
        articles=[article1],
        source_map={str(source.id): source},
        known_company_ids=set(),
        known_topic_ids=set(),
        known_category_ids=set(),
        now=now,
    )
    ctx2 = ClusterRankingContext(
        cluster=cluster2,
        articles=[article2],
        source_map={str(source.id): source},
        known_company_ids=set(),
        known_topic_ids=set(),
        known_category_ids=set(),
        now=now,
    )
    result1 = engine.rank_cluster(ctx1)
    result2 = engine.rank_cluster(ctx2)
    top_result = selector.select_top_story([result1, result2])
    assert top_result.top_story_cluster_id == max(
        str(cluster1.id), str(cluster2.id)
    )


def test_inactive_cluster_excluded():
    engine = StoryRankingEngine()
    selector = TopStorySelector(ranking_engine=engine)
    now = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)
    cluster = _make_cluster(uuid4())
    cluster.status = __import__(
        "ai_news_digest.domain.enums.cluster_status", fromlist=["ClusterStatus"]
    ).ClusterStatus.ARCHIVED
    article = _make_article(uuid4(), uuid4(), cluster_id=cluster.id)
    source = _make_source(article.source_id)
    ctx = ClusterRankingContext(
        cluster=cluster,
        articles=[article],
        source_map={str(source.id): source},
        known_company_ids=set(),
        known_topic_ids=set(),
        known_category_ids=set(),
        now=now,
    )
    result = engine.rank_cluster(ctx)
    ranked, top = selector.rank_and_select(
        clusters=[cluster],
        cluster_articles={str(cluster.id): [article]},
        source_map={str(source.id): source},
        known_company_ids=set(),
        known_topic_ids=set(),
        known_category_ids=set(),
    )
    assert len(ranked) == 0


def test_cluster_without_articles_excluded():
    engine = StoryRankingEngine()
    selector = TopStorySelector(ranking_engine=engine)
    now = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)
    cluster = _make_cluster(uuid4())
    source = _make_source(uuid4())
    ranked, top = selector.rank_and_select(
        clusters=[cluster],
        cluster_articles={str(cluster.id): []},
        source_map={str(source.id): source},
        known_company_ids=set(),
        known_topic_ids=set(),
        known_category_ids=set(),
    )
    assert len(ranked) == 0


__all__ = [
    "test_empty_candidates_returns_none_top_story",
    "test_single_candidate_is_top_story",
    "test_deterministic_tie_breaking",
    "test_inactive_cluster_excluded",
    "test_cluster_without_articles_excluded",
]
