"""
Domain tests for RecommendationEngine.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from ai_news_digest.application.services.personalization.personalized_relevance_engine import (
    PersonalizedRelevanceEngine,
)
from ai_news_digest.application.services.recommendation.constants import (
    RecommendationDefaults,
    RecommendationSignal,
    RecommendationWeights,
    ScoredCluster,
)
from ai_news_digest.application.services.recommendation.recommendation_engine import (
    RecommendationEngine,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.story_activity_status import StoryActivityStatus
from ai_news_digest.domain.enums.trend_status import TrendStatus
from ai_news_digest.domain.enums.trend_type import TrendType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.story_activity import StoryActivity
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.story_event import StoryEvent
from ai_news_digest.domain.models.trend import Trend
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile


def _make_user_preference(**kwargs) -> UserPreferenceProfile:
    defaults = {
        "user_id": uuid4(),
        "followed_company_ids": frozenset(),
        "followed_topic_ids": frozenset(),
        "followed_category_ids": frozenset(),
        "followed_source_ids": frozenset(),
        "muted_company_ids": frozenset(),
        "muted_topic_ids": frozenset(),
        "muted_category_ids": frozenset(),
        "muted_source_ids": frozenset(),
        "min_importance": 0.0,
        "min_confidence": 0.0,
        "feed_sort": "published_at",
        "freshness_window_days": None,
        "preferred_source_types": (),
    }
    defaults.update(kwargs)
    return UserPreferenceProfile(**defaults)


def _make_article(source_id: UUID | None = None, **kwargs) -> Article:
    defaults = {
        "id": uuid4(),
        "title": "Test Article",
        "url": "https://example.com/test",
        "summary": "Summary",
        "content": None,
        "source_id": source_id or uuid4(),
        "category_id": None,
        "published_at": datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
        "fetched_at": datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
        "status": ArticleStatus.READY,
        "importance_score": 0.5,
        "confidence": 0.5,
        "extraction_method": "rss",
        "extraction_quality": "none",
        "extracted_at": None,
        "content_char_count": None,
        "ai_provider": None,
        "ai_model": None,
        "ai_processed_at": None,
        "ai_input_tokens": None,
        "ai_output_tokens": None,
        "ai_prompt_version": None,
        "key_takeaways": (),
        "why_it_matters": None,
        "topics": (),
        "companies": (),
        "categories": (),
        "topic_ids": (),
        "company_ids": (),
        "category_ids": (),
        "cluster_id": None,
    }
    defaults.update(kwargs)
    return Article(**defaults)


def _make_story_cluster() -> StoryCluster:
    return StoryCluster(
        id=uuid4(),
        title="Cluster",
        slug="cluster",
        importance_score=0.9,
        confidence=0.9,
        last_updated_at=datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
    )


def _make_source() -> Source:
    return Source(
        id=uuid4(),
        name="Test Source",
        feed_url="https://example.com/feed",
        website_url="https://example.com",
        description="Test source",
        is_active=True,
        source_type="tech_publication",
        status="active",
    )


def _make_activity(status: StoryActivityStatus) -> StoryActivity:
    return StoryActivity(
        id=uuid4(),
        story_cluster_id=uuid4(),
        status=status,
        activity_score=0.8,
        confidence=0.9,
        explanation="Test activity",
        evaluated_at=datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
        detection_version="v1",
    )


def _make_event(hours_ago: int = 24) -> StoryEvent:
    now = datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC)
    return StoryEvent(
        id=uuid4(),
        story_cluster_id=uuid4(),
        event_type="development",
        title="Test event",
        description="Test event description",
        confidence=0.8,
        event_time=now - __import__("datetime").timedelta(hours=hours_ago),
        sequence=1,
    )


def _make_trend(**kwargs) -> Trend:
    defaults = {
        "id": uuid4(),
        "trend_type": TrendType.COMPANY_TREND,
        "canonical_key": "company:test",
        "display_name": "Test Trend",
        "status": TrendStatus.EMERGING,
        "trend_score": 70.0,
        "momentum_score": 60.0,
        "first_detected_at": datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
        "last_detected_at": datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
        "recent_activity": 10,
        "baseline_activity": 5,
        "source_count": 3,
        "story_count": 2,
        "event_count": 1,
        "explanation": "test",
        "trend_metadata": {},
        "related_company_ids": frozenset(),
        "related_topic_ids": frozenset(),
        "related_category_ids": frozenset(),
    }
    defaults.update(kwargs)
    return Trend(**defaults)


class TestRecommendationEngine:
    def setup_method(self) -> None:
        self._engine = RecommendationEngine()
        self._now = datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC)

    def test_score_is_bounded_zero_to_hundred(self) -> None:
        company_id = uuid4()
        article = _make_article(
            source_id=uuid4(),
            company_ids=(company_id,),
            companies=("Acme",),
            importance_score=1.0,
            confidence=1.0,
            published_at=self._now,
        )
        cluster = _make_story_cluster()
        profile = _make_user_preference(followed_company_ids=frozenset([company_id]))
        result = self._engine.score_cluster(cluster, article, [article], profile, now=self._now)
        assert 0.0 <= result.score <= 100.0

    def test_followed_company_boosts_score(self) -> None:
        company_id = uuid4()
        article = _make_article(
            source_id=uuid4(),
            company_ids=(company_id,),
            companies=("Acme",),
        )
        cluster = _make_story_cluster()
        profile = _make_user_preference(followed_company_ids=frozenset([company_id]))
        result = self._engine.score_cluster(cluster, article, [article], profile, now=self._now)
        assert result.score > 30.0
        assert any("followed company" in r.lower() for r in result.reasons)

    def test_followed_topic_boosts_score(self) -> None:
        topic_id = uuid4()
        article = _make_article(
            source_id=uuid4(),
            topic_ids=(topic_id,),
            topics=("AI",),
        )
        cluster = _make_story_cluster()
        profile = _make_user_preference(followed_topic_ids=frozenset([topic_id]))
        result = self._engine.score_cluster(cluster, article, [article], profile, now=self._now)
        assert result.score > 30.0
        assert any("followed topic" in r.lower() for r in result.reasons)

    def test_breaking_activity_boosts_score(self) -> None:
        article = _make_article(source_id=uuid4())
        cluster = _make_story_cluster()
        profile = _make_user_preference()
        activity = _make_activity(StoryActivityStatus.BREAKING)
        result = self._engine.score_cluster(cluster, article, [article], profile, activity=activity, now=self._now)
        assert result.score > 30.0
        assert any("breaking" in r.lower() for r in result.reasons)

    def test_developing_activity_boosts_score(self) -> None:
        article = _make_article(source_id=uuid4())
        cluster = _make_story_cluster()
        profile = _make_user_preference()
        activity = _make_activity(StoryActivityStatus.DEVELOPING)
        result = self._engine.score_cluster(cluster, article, [article], profile, activity=activity, now=self._now)
        assert result.score > 30.0
        assert any("developing" in r.lower() for r in result.reasons)

    def test_stale_activity_penalizes_score(self) -> None:
        article = _make_article(source_id=uuid4())
        cluster = _make_story_cluster()
        profile = _make_user_preference()
        activity_stale = _make_activity(StoryActivityStatus.STALE)
        activity_developing = _make_activity(StoryActivityStatus.DEVELOPING)
        result_stale = self._engine.score_cluster(cluster, article, [article], profile, activity=activity_stale, now=self._now)
        result_developing = self._engine.score_cluster(cluster, article, [article], profile, activity=activity_developing, now=self._now)
        assert result_stale.score < result_developing.score
        assert any("stale" in r.lower() for r in result_stale.reasons)

    def test_trend_momentum_boosts_score(self) -> None:
        article = _make_article(source_id=uuid4())
        cluster = _make_story_cluster()
        profile = _make_user_preference()
        trend = _make_trend(
            related_company_ids=frozenset([uuid4()]),
            momentum_score=75.0,
        )
        result = self._engine.score_cluster(cluster, article, [article], profile, trend=trend, now=self._now)
        assert result.score > 30.0
        assert any("accelerating" in r.lower() for r in result.reasons)

    def test_recent_event_boosts_score(self) -> None:
        article = _make_article(source_id=uuid4())
        cluster = _make_story_cluster()
        profile = _make_user_preference()
        events = [_make_event(hours_ago=1)]
        result = self._engine.score_cluster(cluster, article, [article], profile, events=events, now=self._now)
        assert result.score > 30.0
        assert any("recent story update" in r.lower() for r in result.reasons)

    def test_multiple_recent_events_boost_score(self) -> None:
        article = _make_article(source_id=uuid4())
        cluster = _make_story_cluster()
        profile = _make_user_preference()
        events = [_make_event(hours_ago=1), _make_event(hours_ago=2)]
        result = self._engine.score_cluster(cluster, article, [article], profile, events=events, now=self._now)
        assert result.score > 30.0
        assert any("multiple recent updates" in r.lower() for r in result.reasons)

    def test_high_importance_boosts_score(self) -> None:
        article = _make_article(source_id=uuid4(), importance_score=0.9)
        cluster = _make_story_cluster()
        profile = _make_user_preference()
        result = self._engine.score_cluster(cluster, article, [article], profile, now=self._now)
        assert result.score > 30.0
        assert any("high importance" in r.lower() for r in result.reasons)

    def test_select_diverse_penalizes_same_company(self) -> None:
        company_id = "11111111-1111-1111-1111-111111111111"
        scored_a = ScoredCluster(
            cluster_id="a",
            article_id="a",
            score=90.0,
            signals=[],
            reasons=["A"],
            company_ids={company_id},
            topic_ids=set(),
            category_ids=set(),
            source_id="s1",
        )
        scored_b = ScoredCluster(
            cluster_id="b",
            article_id="b",
            score=90.0,
            signals=[],
            reasons=["B"],
            company_ids={company_id},
            topic_ids=set(),
            category_ids=set(),
            source_id="s2",
        )
        scored_c = ScoredCluster(
            cluster_id="c",
            article_id="c",
            score=90.0,
            signals=[],
            reasons=["C"],
            company_ids={company_id},
            topic_ids=set(),
            category_ids=set(),
            source_id="s3",
        )
        selected = self._engine.select_diverse([scored_a, scored_b, scored_c], 3)
        assert len(selected) == 3
        assert selected[2].score < 90.0

    def test_select_diverse_allows_different_companies(self) -> None:
        scored_a = ScoredCluster(
            cluster_id="a",
            article_id="a",
            score=90.0,
            signals=[],
            reasons=["A"],
            company_ids={"11111111-1111-1111-1111-111111111111"},
            topic_ids=set(),
            category_ids=set(),
            source_id="s1",
        )
        scored_b = ScoredCluster(
            cluster_id="b",
            article_id="b",
            score=90.0,
            signals=[],
            reasons=["B"],
            company_ids={"22222222-2222-2222-2222-222222222222"},
            topic_ids=set(),
            category_ids=set(),
            source_id="s1",
        )
        selected = self._engine.select_diverse([scored_a, scored_b], 2)
        assert len(selected) == 2

    def test_score_trend_bounded(self) -> None:
        trend = _make_trend(
            related_company_ids=frozenset([uuid4()]),
            trend_score=90.0,
            momentum_score=80.0,
        )
        profile = _make_user_preference(followed_company_ids=frozenset([uuid4()]))
        result = self._engine.score_trend(trend, profile, now=self._now)
        assert 0.0 <= result.score <= 100.0

    def test_score_trend_followed_company(self) -> None:
        company_id = uuid4()
        trend = _make_trend(
            related_company_ids=frozenset([company_id]),
            trend_score=70.0,
            momentum_score=60.0,
        )
        profile = _make_user_preference(followed_company_ids=frozenset([company_id]))
        result = self._engine.score_trend(trend, profile, now=self._now)
        assert result.score > 30.0
        assert any("followed company" in r.lower() for r in result.reasons)

    def test_select_diverse_respects_limit(self) -> None:
        scored = [
            ScoredCluster(
                cluster_id=str(i),
                article_id=str(i),
                score=float(100 - i),
                signals=[],
                reasons=[str(i)],
                company_ids={f"c{i}"},
                topic_ids=set(),
                category_ids=set(),
                source_id=f"s{i}",
            )
            for i in range(10)
        ]
        selected = self._engine.select_diverse(scored, 3)
        assert len(selected) == 3

    def test_muted_entities_do_not_boost(self) -> None:
        company_id = uuid4()
        article = _make_article(
            source_id=uuid4(),
            company_ids=(company_id,),
            companies=("Acme",),
        )
        cluster = _make_story_cluster()
        profile = _make_user_preference(muted_company_ids=frozenset([company_id]))
        result = self._engine.score_cluster(cluster, article, [article], profile, now=self._now)
        assert not any("followed company" in r.lower() for r in result.reasons)


__all__ = ["TestRecommendationEngine"]
