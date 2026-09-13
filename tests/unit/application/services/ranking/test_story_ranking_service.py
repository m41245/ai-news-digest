"""
Unit tests for StoryRankingEngine (M68).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_news_digest.application.services.ranking.constants import (
    RankingDefaults,
    StoryRankingWeights,
)
from ai_news_digest.application.services.ranking.story_ranking_service import (
    ClusterRankingContext,
    StoryRankingEngine,
)
from ai_news_digest.domain.enums.extraction_quality import ExtractionQuality
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.story_cluster import StoryCluster


def _make_cluster(cluster_id, first_published_at=None):
    return StoryCluster(
        id=cluster_id,
        title="Test Cluster",
        slug="test-cluster",
        first_published_at=first_published_at or datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC),
        last_updated_at=datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC),
    )


def _make_source(source_id, source_type=SourceType.TECH_PUBLICATION, status=SourceStatus.VERIFIED):
    return Source(
        id=source_id,
        name=f"Source {source_id}",
        feed_url=f"https://example.com/feed/{source_id}",
        website_url=None,
        description=None,
        is_active=True,
        source_type=source_type,
        status=status,
        created_at=datetime.now(UTC),
    )


def _make_article(
    article_id,
    source_id,
    cluster_id=None,
    published_at=None,
    extraction_quality=ExtractionQuality.FULL,
    company_ids=(),
    topic_ids=(),
    category_ids=(),
):
    from ai_news_digest.domain.enums.article_status import ArticleStatus
    from ai_news_digest.domain.enums.extraction_method import ExtractionMethod

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
        status=ArticleStatus.READY,
        extraction_method=ExtractionMethod.HTML,
        extraction_quality=extraction_quality,
        company_ids=company_ids,
        topic_ids=topic_ids,
        category_ids=category_ids,
        cluster_id=cluster_id,
    )


def test_ranking_score_is_bounded():
    engine = StoryRankingEngine()
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
    assert RankingDefaults.MIN_SCORE <= result.score <= RankingDefaults.MAX_SCORE


def test_ranking_is_deterministic():
    engine = StoryRankingEngine()
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
    result1 = engine.rank_cluster(ctx)
    result2 = engine.rank_cluster(ctx)
    assert result1.score == result2.score
    assert result1.signals == result2.signals
    assert result1.explanation == result2.explanation


def test_recency_signal_decays():
    engine = StoryRankingEngine()
    now = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)
    cluster_new = _make_cluster(
        uuid4(),
        first_published_at=datetime(2026, 9, 13, 11, 0, 0, tzinfo=UTC),
    )
    cluster_old = _make_cluster(
        uuid4(),
        first_published_at=datetime(2026, 9, 12, 12, 0, 0, tzinfo=UTC),
    )
    article_new = _make_article(
        uuid4(),
        uuid4(),
        cluster_id=cluster_new.id,
        published_at=datetime(2026, 9, 13, 11, 0, 0, tzinfo=UTC),
    )
    article_old = _make_article(
        uuid4(),
        uuid4(),
        cluster_id=cluster_old.id,
        published_at=datetime(2026, 9, 12, 12, 0, 0, tzinfo=UTC),
    )
    source = _make_source(uuid4())
    ctx_new = ClusterRankingContext(
        cluster=cluster_new,
        articles=[article_new],
        source_map={str(source.id): source},
        known_company_ids=set(),
        known_topic_ids=set(),
        known_category_ids=set(),
        now=now,
    )
    ctx_old = ClusterRankingContext(
        cluster=cluster_old,
        articles=[article_old],
        source_map={str(source.id): source},
        known_company_ids=set(),
        known_topic_ids=set(),
        known_category_ids=set(),
        now=now,
    )
    result_new = engine.rank_cluster(ctx_new)
    result_old = engine.rank_cluster(ctx_old)
    recency_new = next(s for s in result_new.signals if s.name == "recency")
    recency_old = next(s for s in result_old.signals if s.name == "recency")
    assert recency_new.normalized_value > recency_old.normalized_value


def test_source_trust_signal():
    engine = StoryRankingEngine()
    now = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)
    cluster = _make_cluster(uuid4())
    source_verified = _make_source(uuid4(), status=SourceStatus.VERIFIED)
    article = _make_article(uuid4(), source_verified.id, cluster_id=cluster.id)
    ctx = ClusterRankingContext(
        cluster=cluster,
        articles=[article],
        source_map={str(source_verified.id): source_verified},
        known_company_ids=set(),
        known_topic_ids=set(),
        known_category_ids=set(),
        now=now,
    )
    result = engine.rank_cluster(ctx)
    trust_signal = next(s for s in result.signals if s.name == "source_trust")
    assert trust_signal.normalized_value > 0.0


def test_official_announcement_signal():
    engine = StoryRankingEngine()
    now = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)
    cluster = _make_cluster(uuid4())
    source_official = _make_source(uuid4(), source_type=SourceType.OFFICIAL_COMPANY)
    article = _make_article(uuid4(), source_official.id, cluster_id=cluster.id)
    ctx = ClusterRankingContext(
        cluster=cluster,
        articles=[article],
        source_map={str(source_official.id): source_official},
        known_company_ids=set(),
        known_topic_ids=set(),
        known_category_ids=set(),
        now=now,
    )
    result = engine.rank_cluster(ctx)
    signal = next(s for s in result.signals if s.name == "official_announcement")
    assert signal.normalized_value == 1.0


def test_corroboration_signal():
    engine = StoryRankingEngine()
    now = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)
    cluster = _make_cluster(uuid4())
    source1 = _make_source(uuid4())
    source2 = _make_source(uuid4())
    article1 = _make_article(uuid4(), source1.id, cluster_id=cluster.id)
    article2 = _make_article(uuid4(), source2.id, cluster_id=cluster.id)
    ctx = ClusterRankingContext(
        cluster=cluster,
        articles=[article1, article2],
        source_map={str(source1.id): source1, str(source2.id): source2},
        known_company_ids=set(),
        known_topic_ids=set(),
        known_category_ids=set(),
        now=now,
    )
    result = engine.rank_cluster(ctx)
    signal = next(s for s in result.signals if s.name == "corroboration")
    assert signal.normalized_value > 0.0


def test_empty_articles_returns_zero_score():
    engine = StoryRankingEngine()
    now = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)
    cluster = _make_cluster(
        uuid4(),
        first_published_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    ctx = ClusterRankingContext(
        cluster=cluster,
        articles=[],
        source_map={},
        known_company_ids=set(),
        known_topic_ids=set(),
        known_category_ids=set(),
        now=now,
    )
    result = engine.rank_cluster(ctx)
    assert result.score == pytest.approx(0.0, abs=1e-6)


def test_weights_normalize_to_one():
    weights_sum = (
        StoryRankingWeights.RECENCY
        + StoryRankingWeights.SOURCE_TRUST
        + StoryRankingWeights.SOURCE_DIVERSITY
        + StoryRankingWeights.CORROBORATION
        + StoryRankingWeights.COMPANY_RELEVANCE
        + StoryRankingWeights.CATEGORY_TOPIC_RELEVANCE
        + StoryRankingWeights.ARTICLE_QUALITY
        + StoryRankingWeights.OFFICIAL_ANNOUNCEMENT
    )
    assert abs(weights_sum - 1.0) < 1e-9


def test_custom_weights_are_normalized():
    engine = StoryRankingEngine(
        recency_weight=1.0,
        source_trust_weight=0.0,
        source_diversity_weight=0.0,
        corroboration_weight=0.0,
        company_relevance_weight=0.0,
        category_topic_relevance_weight=0.0,
        article_quality_weight=0.0,
        official_announcement_weight=0.0,
    )
    assert abs(engine._recency_weight - 1.0) < 1e-9
    assert abs(engine._source_trust_weight - 0.0) < 1e-9


def test_negative_weights_rejected():
    with pytest.raises(ValueError):
        StoryRankingEngine(recency_weight=-1.0)


def test_zero_total_weight_rejected():
    with pytest.raises(ValueError):
        StoryRankingEngine(
            recency_weight=0.0,
            source_trust_weight=0.0,
            source_diversity_weight=0.0,
            corroboration_weight=0.0,
            company_relevance_weight=0.0,
            category_topic_relevance_weight=0.0,
            article_quality_weight=0.0,
            official_announcement_weight=0.0,
        )


__all__ = [
    "test_corroboration_signal",
    "test_custom_weights_are_normalized",
    "test_empty_articles_returns_zero_score",
    "test_negative_weights_rejected",
    "test_official_announcement_signal",
    "test_ranking_is_deterministic",
    "test_ranking_score_is_bounded",
    "test_recency_signal_decays",
    "test_source_trust_signal",
    "test_weights_normalize_to_one",
    "test_zero_total_weight_rejected",
]
