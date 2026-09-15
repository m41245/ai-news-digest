"""
Domain tests for PersonalizedRelevanceEngine.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_news_digest.application.services.personalization.personalized_relevance_engine import (
    PersonalizedRelevanceEngine,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.trend_status import TrendStatus
from ai_news_digest.domain.enums.trend_type import TrendType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_cluster import StoryCluster
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


class TestPersonalizedRelevanceEngine:
    def setup_method(self) -> None:
        self._engine = PersonalizedRelevanceEngine()

    def test_followed_company_boosts_article_score(self) -> None:
        company_id = uuid4()
        article = _make_article(company_ids=(company_id,), companies=("Acme",))
        profile = _make_user_preference(followed_company_ids=frozenset([company_id]))
        result = self._engine.score_article(article, profile)
        assert result.score > 0
        assert any("followed company" in r.lower() for r in result.all_reasons)

    def test_followed_topic_boosts_article_score(self) -> None:
        topic_id = uuid4()
        article = _make_article(topic_ids=(topic_id,), topics=("AI",))
        profile = _make_user_preference(followed_topic_ids=frozenset([topic_id]))
        result = self._engine.score_article(article, profile)
        assert result.score > 0
        assert any("followed topic" in r.lower() for r in result.all_reasons)

    def test_followed_category_boosts_article_score(self) -> None:
        category_id = uuid4()
        article = _make_article(category_ids=(category_id,), categories=("Tech",))
        profile = _make_user_preference(followed_category_ids=frozenset([category_id]))
        result = self._engine.score_article(article, profile)
        assert result.score > 0
        assert any("followed category" in r.lower() for r in result.all_reasons)

    def test_followed_source_boosts_article_score(self) -> None:
        source_id = uuid4()
        article = _make_article(source_id=source_id)
        profile = _make_user_preference(followed_source_ids=frozenset([source_id]))
        result = self._engine.score_article(article, profile)
        assert result.score > 0
        assert any("followed source" in r.lower() for r in result.all_reasons)

    def test_muted_entities_are_excluded_before_scoring(self) -> None:
        company_id = uuid4()
        article = _make_article(company_ids=(company_id,))
        profile = _make_user_preference(muted_company_ids=frozenset([company_id]))
        result = self._engine.score_article(article, profile)
        assert not any("muted" in r.lower() for r in result.all_reasons)
        assert not any("followed company" in r.lower() for r in result.all_reasons)

    def test_multiple_matches_accumulate_score(self) -> None:
        company_id = uuid4()
        topic_id = uuid4()
        category_id = uuid4()
        source_id = uuid4()
        article = _make_article(
            source_id=source_id,
            company_ids=(company_id,),
            topic_ids=(topic_id,),
            category_ids=(category_id,),
        )
        profile = _make_user_preference(
            followed_company_ids=frozenset([company_id]),
            followed_topic_ids=frozenset([topic_id]),
            followed_category_ids=frozenset([category_id]),
            followed_source_ids=frozenset([source_id]),
        )
        result = self._engine.score_article(article, profile)
        assert result.score > 0

    def test_no_preferences_returns_fallback(self) -> None:
        article = _make_article()
        profile = _make_user_preference()
        result = self._engine.score_article(article, profile)
        assert any("fallback" in r.lower() or "coverage" in r.lower() for r in result.all_reasons)

    def test_score_is_bounded(self) -> None:
        company_id = uuid4()
        topic_id = uuid4()
        category_id = uuid4()
        source_id = uuid4()
        article = _make_article(
            source_id=source_id,
            company_ids=(company_id,),
            topic_ids=(topic_id,),
            category_ids=(category_id,),
            importance_score=1.0,
            confidence=1.0,
        )
        profile = _make_user_preference(
            followed_company_ids=frozenset([company_id]),
            followed_topic_ids=frozenset([topic_id]),
            followed_category_ids=frozenset([category_id]),
            followed_source_ids=frozenset([source_id]),
            preferred_source_types=("official_company",),
        )
        result = self._engine.score_article(article, profile)
        assert result.score <= 100.0

    def test_trend_matching_followed_company(self) -> None:
        company_id = uuid4()
        trend = _make_trend(
            related_company_ids=frozenset([company_id]),
            trend_score=70.0,
            momentum_score=60.0,
        )
        profile = _make_user_preference(followed_company_ids=frozenset([company_id]))
        result = self._engine.score_trend(trend, profile)
        assert result.score > 0
        assert any("followed company" in r.lower() for r in result.all_reasons)

    def test_trend_matching_muted_company_is_filtered_before_scoring(self) -> None:
        company_id = uuid4()
        trend = _make_trend(
            related_company_ids=frozenset([company_id]),
            trend_score=70.0,
            momentum_score=60.0,
        )
        profile = _make_user_preference(muted_company_ids=frozenset([company_id]))
        result = self._engine.score_trend(trend, profile)
        assert not any("followed company" in r.lower() for r in result.all_reasons)

    def test_trend_no_matches_returns_fallback(self) -> None:
        trend = _make_trend(trend_score=10.0, momentum_score=5.0)
        profile = _make_user_preference()
        result = self._engine.score_trend(trend, profile)
        assert any(
            "fallback" in r.lower() or "active trend" in r.lower()
            for r in result.all_reasons
        )
