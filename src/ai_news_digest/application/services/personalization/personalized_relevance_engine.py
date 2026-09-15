"""
Personalized relevance engine for deterministic, explainable content scoring.

Reuses RankingWeights and RankingExplanation from the ranking module to keep
weights centralized and ensure global ranking and personalized relevance
remain independent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ai_news_digest.application.services.ranking.constants import (
    RankingExplanation,
    RankingWeights,
)
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.trend import Trend
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile


class PersonalizedRelevanceEngine:
    """Compute a deterministic personalized relevance score for content.

    Mute precedence is enforced by the caller (muted entities are excluded
    before scoring). The engine only evaluates matches against the active
    preference sets.
    """

    def __init__(self) -> None:
        self._weights = RankingWeights

    def score_article(
        self,
        article: Article,
        profile: UserPreferenceProfile,
        source_map: dict[Any, Any] | None = None,
        now: datetime | None = None,
    ) -> RankingExplanation:
        """Score a single article against user preferences."""
        if now is None:
            now = datetime.now(UTC)
        explanation = RankingExplanation()

        article_company_ids = set(article.company_ids)
        article_topic_ids = set(article.topic_ids)
        article_category_ids = set(article.category_ids)
        if article.category_id:
            article_category_ids.add(article.category_id)

        if article_company_ids & profile.followed_company_ids:
            explanation.add_personalization(
                "Matches followed company", self._weights.FOLLOWED_COMPANY
            )

        if article_topic_ids & profile.followed_topic_ids:
            explanation.add_personalization(
                "Matches followed topic", self._weights.FOLLOWED_TOPIC
            )

        if article_category_ids & profile.followed_category_ids:
            explanation.add_personalization(
                "Matches followed category", self._weights.FOLLOWED_CATEGORY
            )

        if profile.followed_source_ids and article.source_id in profile.followed_source_ids:
            explanation.add_personalization(
                "Matches followed source", self._weights.FOLLOWED_SOURCE
            )

        if (article.importance_score or 0) >= self._weights.HIGH_IMPORTANCE_THRESHOLD:
            explanation.add_quality("High importance", self._weights.HIGH_IMPORTANCE)

        if (article.confidence or 0) >= self._weights.STRONG_CONFIDENCE_THRESHOLD:
            explanation.add_quality("Strong confidence", self._weights.STRONG_CONFIDENCE)

        if article.published_at >= now - __import__("datetime").timedelta(
            hours=self._weights.FRESH_COVERAGE_HOURS
        ):
            explanation.add_freshness("Fresh coverage", self._weights.FRESH_COVERAGE)

        if source_map and article.source_id in source_map:
            source = source_map[article.source_id]
            if source.source_type.value in (profile.preferred_source_types or ()):
                explanation.add_personalization(
                    "Preferred source type", self._weights.PREFERRED_SOURCE_TYPE
                )

        if not explanation.all_reasons:
            explanation.add_fallback("Recent coverage")

        return explanation

    def score_story_cluster(
        self,
        cluster: StoryCluster,
        representative: Article,
        cluster_articles: list[Article],
        profile: UserPreferenceProfile,
        source_map: dict[Any, Any] | None = None,
        now: datetime | None = None,
    ) -> RankingExplanation:
        """Score a story cluster against user preferences."""
        if now is None:
            now = datetime.now(UTC)
        explanation = RankingExplanation()

        article_company_ids = {cid for a in cluster_articles for cid in a.company_ids}
        article_topic_ids = {tid for a in cluster_articles for tid in a.topic_ids}
        article_category_ids = {cid for a in cluster_articles for cid in a.category_ids}
        if representative.category_id:
            article_category_ids.add(representative.category_id)

        if article_company_ids & profile.followed_company_ids:
            explanation.add_personalization(
                "Matches followed company", self._weights.FOLLOWED_COMPANY
            )

        if article_topic_ids & profile.followed_topic_ids:
            explanation.add_personalization(
                "Matches followed topic", self._weights.FOLLOWED_TOPIC
            )

        if article_category_ids & profile.followed_category_ids:
            explanation.add_personalization(
                "Matches followed category", self._weights.FOLLOWED_CATEGORY
            )

        if profile.followed_source_ids and representative.source_id in profile.followed_source_ids:
            explanation.add_personalization(
                "Matches followed source", self._weights.FOLLOWED_SOURCE
            )

        if (cluster.importance_score or 0) >= self._weights.HIGH_IMPORTANCE_THRESHOLD:
            explanation.add_quality("High importance", self._weights.HIGH_IMPORTANCE)

        source_count = len({a.source_id for a in cluster_articles})
        if source_count >= self._weights.MULTIPLE_SOURCES_MIN:
            explanation.add_quality(
                "Multiple independent sources", self._weights.MULTIPLE_SOURCES
            )

        if cluster.last_updated_at >= now - __import__("datetime").timedelta(
            days=self._weights.RECENTLY_UPDATED_DAYS
        ):
            explanation.add_freshness(
                "Recently updated story", self._weights.RECENTLY_UPDATED
            )

        if (cluster.confidence or 0) >= self._weights.STRONG_CONFIDENCE_THRESHOLD:
            explanation.add_quality("Strong confidence", self._weights.STRONG_CONFIDENCE)

        if representative.published_at >= now - __import__("datetime").timedelta(
            hours=self._weights.FRESH_COVERAGE_HOURS
        ):
            explanation.add_freshness("Fresh coverage", self._weights.FRESH_COVERAGE)

        if source_map and representative.source_id in source_map:
            source = source_map[representative.source_id]
            if source.source_type.value in (profile.preferred_source_types or ()):
                explanation.add_personalization(
                    "Preferred source type", self._weights.PREFERRED_SOURCE_TYPE
                )

        if not explanation.all_reasons:
            explanation.add_fallback("Recent coverage")

        return explanation

    def score_trend(
        self,
        trend: Trend,
        profile: UserPreferenceProfile,
    ) -> RankingExplanation:
        """Score a trend against user preferences using related entity IDs."""
        explanation = RankingExplanation()
        company_ids = trend.related_company_ids
        topic_ids = trend.related_topic_ids
        category_ids = trend.related_category_ids

        if company_ids and company_ids & profile.followed_company_ids:
            explanation.add_personalization(
                "Matches followed company", self._weights.FOLLOWED_COMPANY
            )

        if topic_ids and topic_ids & profile.followed_topic_ids:
            explanation.add_personalization(
                "Matches followed topic", self._weights.FOLLOWED_TOPIC
            )

        if category_ids and category_ids & profile.followed_category_ids:
            explanation.add_personalization(
                "Matches followed category", self._weights.FOLLOWED_CATEGORY
            )

        if trend.trend_score >= 65:
            explanation.add_quality("Emerging trend", 0.3)

        if trend.momentum_score >= 60:
            explanation.add_freshness("Strong momentum", 0.2)

        if not explanation.all_reasons:
            explanation.add_fallback("Active trend")

        return explanation

    @staticmethod
    def _parse_related_ids(raw: str) -> frozenset[Any]:
        from uuid import UUID

        ids: list[Any] = []
        for part in raw.split(","):
            part = part.strip()
            if part:
                try:
                    ids.append(UUID(part))
                except ValueError:
                    continue
        return frozenset(ids)


__all__ = ["PersonalizedRelevanceEngine"]
