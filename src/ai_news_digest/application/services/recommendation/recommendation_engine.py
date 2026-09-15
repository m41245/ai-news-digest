"""
Advanced recommendation engine for deterministic, explainable content scoring.

Combines multiple signals into a bounded 0-100 recommendation score:

    Global Importance
    + M86 Personal Relevance
    + Freshness
    + Story Activity
    + Trend Momentum
    + Story Evolution
    + Diversity (selection-time)
    + Novelty (selection-time)
    -> Personalized Recommendation Score

The engine is independent of HTTP, SQLAlchemy, and any specific LLM provider.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ai_news_digest.application.services.personalization.personalized_relevance_engine import (
    PersonalizedRelevanceEngine,
)
from ai_news_digest.application.services.recommendation.constants import (
    RecommendationDefaults,
    RecommendationSignal,
    RecommendationWeights,
    ScoredCluster,
)
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_activity import StoryActivity
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.story_event import StoryEvent
from ai_news_digest.domain.models.trend import Trend
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile


class RecommendationEngine:
    """Compute a deterministic personalized recommendation score for content.

    The engine is pure where practical: all database access is performed by
    the caller. The engine only evaluates signals against the provided data.
    """

    def __init__(self) -> None:
        self._weights = RecommendationWeights
        self._relevance_engine = PersonalizedRelevanceEngine()

    def score_cluster(
        self,
        cluster: StoryCluster,
        representative: Article,
        cluster_articles: list[Article],
        profile: UserPreferenceProfile,
        activity: StoryActivity | None = None,
        trend: Trend | None = None,
        events: list[StoryEvent] | None = None,
        source_map: dict[Any, Any] | None = None,
        now: datetime | None = None,
    ) -> ScoredCluster:
        """Score a story cluster for recommendation.

        Returns a ScoredCluster with a bounded 0-100 score and structured
        signals/explanations. Mute precedence is enforced by the caller
        (muted entities are excluded before scoring).
        """
        if now is None:
            now = datetime.now(UTC)
        signals: list[RecommendationSignal] = []
        reasons: list[str] = []
        score = self._weights.BASE_SCORE

        article_company_ids = {cid for a in cluster_articles for cid in a.company_ids}
        article_topic_ids = {tid for a in cluster_articles for tid in a.topic_ids}
        article_category_ids = {cid for a in cluster_articles for cid in a.category_ids}
        if representative.category_id:
            article_category_ids.add(representative.category_id)

        relevance_explanation = self._relevance_engine.score_story_cluster(
            cluster=cluster,
            representative=representative,
            cluster_articles=cluster_articles,
            profile=profile,
            source_map=source_map,
            now=now,
        )
        mapped_preference_score = min(50.0, relevance_explanation.score * 20.0)
        if mapped_preference_score > 0:
            score += mapped_preference_score
            for reason in relevance_explanation.personalization:
                signals.append(
                    RecommendationSignal(
                        name="preference",
                        raw_value=mapped_preference_score,
                        contribution=mapped_preference_score,
                        explanation=reason,
                    )
                )
                reasons.append(reason)

        if (cluster.importance_score or 0) >= 0.8:
            importance_boost = self._weights.HIGH_IMPORTANCE
            score = max(
                self._weights.MIN_SCORE,
                min(self._weights.MAX_SCORE, score + importance_boost),
            )
            signals.append(
                RecommendationSignal(
                    name="global_importance",
                    raw_value=cluster.importance_score or 0,
                    contribution=importance_boost,
                    explanation="High importance story",
                )
            )
            reasons.append("High importance story")

        source_count = len({a.source_id for a in cluster_articles})
        if source_count >= 3:
            multi_source_boost = self._weights.MULTIPLE_SOURCES
            score = max(
                self._weights.MIN_SCORE,
                min(self._weights.MAX_SCORE, score + multi_source_boost),
            )
            signals.append(
                RecommendationSignal(
                    name="multiple_sources",
                    raw_value=float(source_count),
                    contribution=multi_source_boost,
                    explanation=f"Multiple independent sources ({source_count})",
                )
            )
            reasons.append(f"Multiple independent sources ({source_count})")

        if cluster.last_updated_at >= now - __import__("datetime").timedelta(
            days=7
        ):
            updated_boost = self._weights.RECENTLY_UPDATED
            score = max(
                self._weights.MIN_SCORE,
                min(self._weights.MAX_SCORE, score + updated_boost),
            )
            signals.append(
                RecommendationSignal(
                    name="recently_updated",
                    raw_value=1.0,
                    contribution=updated_boost,
                    explanation="Recently updated story",
                )
            )
            reasons.append("Recently updated story")

        if (cluster.confidence or 0) >= 0.9:
            confidence_boost = self._weights.STRONG_CONFIDENCE
            score = max(
                self._weights.MIN_SCORE,
                min(self._weights.MAX_SCORE, score + confidence_boost),
            )
            signals.append(
                RecommendationSignal(
                    name="strong_confidence",
                    raw_value=cluster.confidence or 0,
                    contribution=confidence_boost,
                    explanation="Strong confidence",
                )
            )
            reasons.append("Strong confidence")

        if representative.published_at >= now - __import__("datetime").timedelta(
            hours=24
        ):
            fresh_boost = self._weights.FRESH_COVERAGE
            score = max(
                self._weights.MIN_SCORE,
                min(self._weights.MAX_SCORE, score + fresh_boost),
            )
            signals.append(
                RecommendationSignal(
                    name="fresh_coverage",
                    raw_value=1.0,
                    contribution=fresh_boost,
                    explanation="Fresh coverage",
                )
            )
            reasons.append("Fresh coverage")

        if activity is not None:
            activity_status = (
                activity.status.value
                if hasattr(activity.status, "value")
                else str(activity.status)
            )
            if activity_status == "breaking":
                activity_boost = self._weights.BREAKING_STORY
                score = max(
                    self._weights.MIN_SCORE,
                    min(self._weights.MAX_SCORE, score + activity_boost),
                )
                signals.append(
                    RecommendationSignal(
                        name="story_activity",
                        raw_value=activity.activity_score,
                        contribution=activity_boost,
                        explanation="Breaking story",
                    )
                )
                reasons.append("Breaking story")
            elif activity_status == "developing":
                activity_boost = self._weights.DEVELOPING_STORY
                score = max(
                    self._weights.MIN_SCORE,
                    min(self._weights.MAX_SCORE, score + activity_boost),
                )
                signals.append(
                    RecommendationSignal(
                        name="story_activity",
                        raw_value=activity.activity_score,
                        contribution=activity_boost,
                        explanation="Developing story",
                    )
                )
                reasons.append("Developing story")
            elif activity_status == "ongoing":
                activity_boost = self._weights.ONGOING_STORY
                score = max(
                    self._weights.MIN_SCORE,
                    min(self._weights.MAX_SCORE, score + activity_boost),
                )
                signals.append(
                    RecommendationSignal(
                        name="story_activity",
                        raw_value=activity.activity_score,
                        contribution=activity_boost,
                        explanation="Ongoing story",
                    )
                )
                reasons.append("Ongoing story")
            elif activity_status == "stale":
                activity_boost = self._weights.STALE_PENALTY
                score = max(
                    self._weights.MIN_SCORE,
                    min(self._weights.MAX_SCORE, score + activity_boost),
                )
                signals.append(
                    RecommendationSignal(
                        name="story_activity",
                        raw_value=activity.activity_score,
                        contribution=activity_boost,
                        explanation="Stale story",
                    )
                )
                reasons.append("Stale story")

        if trend is not None:
            story_company_ids = article_company_ids
            story_topic_ids = article_topic_ids
            story_category_ids = article_category_ids

            additional_company = trend.related_company_ids - story_company_ids
            additional_topic = trend.related_topic_ids - story_topic_ids
            additional_category = trend.related_category_ids - story_category_ids

            trend_match_ids = additional_company | additional_topic | additional_category

            if trend_match_ids:
                if trend.momentum_score >= 70:
                    trend_boost = self._weights.TREND_STRONG_MOMENTUM
                    trend_explanation = "Strong accelerating trend"
                elif trend.momentum_score >= 50:
                    trend_boost = self._weights.TREND_MOMENTUM
                    trend_explanation = "Trend with momentum"
                else:
                    trend_boost = 0.0
                    trend_explanation = ""

                if trend_boost > 0:
                    score = max(
                        self._weights.MIN_SCORE,
                        min(self._weights.MAX_SCORE, score + trend_boost),
                    )
                    signals.append(
                        RecommendationSignal(
                            name="trend_momentum",
                            raw_value=trend.momentum_score,
                            contribution=trend_boost,
                            explanation=trend_explanation,
                        )
                    )
                    reasons.append(trend_explanation)

        if events:
            recent_cutoff = now - __import__("datetime").timedelta(
                hours=RecommendationDefaults.RECENT_EVENT_HOURS
            )
            recent_events = [
                e for e in events
                if e.event_time is not None and e.event_time >= recent_cutoff
            ]
            if recent_events:
                evolution_boost = self._weights.RECENT_EVENT
                score = max(
                    self._weights.MIN_SCORE,
                    min(self._weights.MAX_SCORE, score + evolution_boost),
                )
                signals.append(
                    RecommendationSignal(
                        name="story_evolution",
                        raw_value=float(len(recent_events)),
                        contribution=evolution_boost,
                        explanation="Recent story update",
                    )
                )
                reasons.append("Recent story update")
                if len(recent_events) > 1:
                    multi_event_boost = self._weights.MULTIPLE_EVENTS
                    score = max(
                        self._weights.MIN_SCORE,
                        min(self._weights.MAX_SCORE, score + multi_event_boost),
                    )
                    signals.append(
                        RecommendationSignal(
                            name="story_evolution",
                            raw_value=float(len(recent_events)),
                            contribution=multi_event_boost,
                            explanation="Multiple recent updates",
                        )
                    )
                    reasons.append("Multiple recent updates")

        if not reasons:
            reasons.append("Recommended based on general relevance")
            signals.append(
                RecommendationSignal(
                    name="fallback",
                    raw_value=0.0,
                    contribution=0.0,
                    explanation="Recommended based on general relevance",
                )
            )

        score = max(self._weights.MIN_SCORE, min(self._weights.MAX_SCORE, score))

        return ScoredCluster(
            cluster_id=str(cluster.id),
            article_id=str(representative.id),
            score=score,
            signals=signals,
            reasons=reasons,
            company_ids={str(cid) for cid in article_company_ids},
            topic_ids={str(tid) for tid in article_topic_ids},
            category_ids={str(cid) for cid in article_category_ids},
            source_id=str(representative.source_id) if representative.source_id else None,
        )

    def select_diverse(
        self,
        scored_clusters: list[ScoredCluster],
        limit: int,
    ) -> list[ScoredCluster]:
        """Apply bounded diversity selection to a sorted list of scored clusters.

        Prevents returning excessive recommendations from the same company,
        topic, category, or source when better alternatives exist. The input
        list should already be sorted by score descending.
        """
        if limit <= 0:
            return []

        selected: list[ScoredCluster] = []
        company_count: dict[str, int] = {}
        topic_count: dict[str, int] = {}
        category_count: dict[str, int] = {}
        source_count: dict[str, int] = {}

        for item in scored_clusters:
            if len(selected) >= limit:
                break

            if any(selected_item.cluster_id == item.cluster_id for selected_item in selected):
                continue

            company_penalty = 0.0
            topic_penalty = 0.0
            category_penalty = 0.0
            source_penalty = 0.0

            for cid in item.company_ids:
                if company_count.get(cid, 0) >= RecommendationDefaults.MAX_SAME_COMPANY:
                    company_penalty = min(company_penalty, RecommendationDefaults.DIVERSITY_PENALTY)

            for tid in item.topic_ids:
                if topic_count.get(tid, 0) >= RecommendationDefaults.MAX_SAME_TOPIC:
                    topic_penalty = min(topic_penalty, RecommendationDefaults.DIVERSITY_PENALTY)

            for cid in item.category_ids:
                if category_count.get(cid, 0) >= RecommendationDefaults.MAX_SAME_CATEGORY:
                    category_penalty = min(
                        category_penalty, RecommendationDefaults.DIVERSITY_PENALTY
                    )

            if (
                item.source_id
                and source_count.get(item.source_id, 0) >= RecommendationDefaults.MAX_SAME_SOURCE
            ):
                source_penalty = min(
                    source_penalty, RecommendationDefaults.DIVERSITY_PENALTY
                )

            adjusted_score = max(
                self._weights.MIN_SCORE,
                min(
                    self._weights.MAX_SCORE,
                    item.score
                    + company_penalty
                    + topic_penalty
                    + category_penalty
                    + source_penalty,
                ),
            )

            if adjusted_score <= 0:
                continue

            selected.append(
                ScoredCluster(
                    cluster_id=item.cluster_id,
                    article_id=item.article_id,
                    score=adjusted_score,
                    signals=item.signals,
                    reasons=item.reasons,
                    company_ids=item.company_ids,
                    topic_ids=item.topic_ids,
                    category_ids=item.category_ids,
                    source_id=item.source_id,
                )
            )

            for cid in item.company_ids:
                company_count[cid] = company_count.get(cid, 0) + 1
            for tid in item.topic_ids:
                topic_count[tid] = topic_count.get(tid, 0) + 1
            for cid in item.category_ids:
                category_count[cid] = category_count.get(cid, 0) + 1
            if item.source_id:
                source_count[item.source_id] = source_count.get(item.source_id, 0) + 1

        return selected

    def score_trend(
        self,
        trend: Trend,
        profile: UserPreferenceProfile,
        now: datetime | None = None,
    ) -> ScoredCluster:
        """Score a trend for recommendation."""
        if now is None:
            now = datetime.now(UTC)
        signals: list[RecommendationSignal] = []
        reasons: list[str] = []
        score = self._weights.BASE_SCORE

        company_ids = trend.related_company_ids
        topic_ids = trend.related_topic_ids
        category_ids = trend.related_category_ids

        if company_ids & profile.followed_company_ids:
            boost = self._weights.FOLLOWED_COMPANY
            score = max(self._weights.MIN_SCORE, min(self._weights.MAX_SCORE, score + boost))
            signals.append(
                RecommendationSignal(
                    name="preference",
                    raw_value=float(len(company_ids & profile.followed_company_ids)),
                    contribution=boost,
                    explanation="Matches followed company",
                )
            )
            reasons.append("Matches followed company")

        if topic_ids & profile.followed_topic_ids:
            boost = self._weights.FOLLOWED_TOPIC
            score = max(self._weights.MIN_SCORE, min(self._weights.MAX_SCORE, score + boost))
            signals.append(
                RecommendationSignal(
                    name="preference",
                    raw_value=float(len(topic_ids & profile.followed_topic_ids)),
                    contribution=boost,
                    explanation="Matches followed topic",
                )
            )
            reasons.append("Matches followed topic")

        if category_ids & profile.followed_category_ids:
            boost = self._weights.FOLLOWED_CATEGORY
            score = max(self._weights.MIN_SCORE, min(self._weights.MAX_SCORE, score + boost))
            signals.append(
                RecommendationSignal(
                    name="preference",
                    raw_value=float(len(category_ids & profile.followed_category_ids)),
                    contribution=boost,
                    explanation="Matches followed category",
                )
            )
            reasons.append("Matches followed category")

        if trend.trend_score >= 70:
            trend_boost = self._weights.TREND_STRONG_MOMENTUM
            score = max(self._weights.MIN_SCORE, min(self._weights.MAX_SCORE, score + trend_boost))
            signals.append(
                RecommendationSignal(
                    name="trend_momentum",
                    raw_value=trend.trend_score,
                    contribution=trend_boost,
                    explanation="Strong trend signal",
                )
            )
            reasons.append("Strong trend signal")
        elif trend.trend_score >= 50:
            trend_boost = self._weights.TREND_MOMENTUM
            score = max(self._weights.MIN_SCORE, min(self._weights.MAX_SCORE, score + trend_boost))
            signals.append(
                RecommendationSignal(
                    name="trend_momentum",
                    raw_value=trend.trend_score,
                    contribution=trend_boost,
                    explanation="Trending",
                )
            )
            reasons.append("Trending")

        if trend.momentum_score >= 70:
            momentum_boost = self._weights.TREND_STRONG_MOMENTUM
            score = max(
                self._weights.MIN_SCORE,
                min(self._weights.MAX_SCORE, score + momentum_boost),
            )
            signals.append(
                RecommendationSignal(
                    name="trend_momentum",
                    raw_value=trend.momentum_score,
                    contribution=momentum_boost,
                    explanation="Strong accelerating trend",
                )
            )
            reasons.append("Strong accelerating trend")
        elif trend.momentum_score >= 50:
            momentum_boost = self._weights.TREND_MOMENTUM
            score = max(
                self._weights.MIN_SCORE,
                min(self._weights.MAX_SCORE, score + momentum_boost),
            )
            signals.append(
                RecommendationSignal(
                    name="trend_momentum",
                    raw_value=trend.momentum_score,
                    contribution=momentum_boost,
                    explanation="Trend with momentum",
                )
            )
            reasons.append("Trend with momentum")

        if not reasons:
            reasons.append("Active trend")
            signals.append(
                RecommendationSignal(
                    name="fallback",
                    raw_value=0.0,
                    contribution=0.0,
                    explanation="Active trend",
                )
            )

        score = max(self._weights.MIN_SCORE, min(self._weights.MAX_SCORE, score))

        return ScoredCluster(
            cluster_id=str(trend.id),
            article_id="",
            score=score,
            signals=signals,
            reasons=reasons,
            company_ids={str(cid) for cid in company_ids},
            topic_ids={str(tid) for tid in topic_ids},
            category_ids={str(cid) for cid in category_ids},
            source_id=None,
        )


__all__ = ["RecommendationEngine"]
