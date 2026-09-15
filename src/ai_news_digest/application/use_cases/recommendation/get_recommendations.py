"""
Use case for retrieving personalized recommendations.

Combines story clusters and trends into a single ranked recommendation list
using the RecommendationEngine.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from ai_news_digest.application.dto.recommendation import (
    RecommendationItemResponse,
    RecommendationResponse,
    RecommendationSort,
)
from ai_news_digest.application.services.recommendation.constants import (
    RecommendationDefaults,
    ScoredCluster,
)
from ai_news_digest.application.services.recommendation.recommendation_engine import (
    RecommendationEngine,
)
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.trend import Trend
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.category_repository import CategoryRepository
from ai_news_digest.domain.ports.company_repository import CompanyRepository
from ai_news_digest.domain.ports.source_repository import SourceRepository
from ai_news_digest.domain.ports.story_activity_repository import StoryActivityRepository
from ai_news_digest.domain.ports.story_cluster_repository import StoryClusterRepository
from ai_news_digest.domain.ports.story_event_repository import StoryEventRepository
from ai_news_digest.domain.ports.trend_repository import TrendRepository
from ai_news_digest.domain.ports.user_preference_repository import UserPreferenceRepository


class GetRecommendationsUseCase:
    """Return a deterministic, explainable personalized recommendation list."""

    def __init__(
        self,
        preference_repository: UserPreferenceRepository,
        article_repository: ArticleRepository,
        story_cluster_repository: StoryClusterRepository,
        source_repository: SourceRepository,
        category_repository: CategoryRepository,
        company_repository: CompanyRepository,
        story_activity_repository: StoryActivityRepository,
        story_event_repository: StoryEventRepository,
        trend_repository: TrendRepository,
    ) -> None:
        self._preference_repository = preference_repository
        self._article_repository = article_repository
        self._story_cluster_repository = story_cluster_repository
        self._source_repository = source_repository
        self._category_repository = category_repository
        self._company_repository = company_repository
        self._story_activity_repository = story_activity_repository
        self._story_event_repository = story_event_repository
        self._trend_repository = trend_repository
        self._engine = RecommendationEngine()

    async def execute(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = RecommendationDefaults.DEFAULT_RECOMMENDATION_LIMIT,
        sort: RecommendationSort = "recommendation",
    ) -> RecommendationResponse:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = RecommendationDefaults.DEFAULT_RECOMMENDATION_LIMIT
        if page_size > RecommendationDefaults.MAX_RECOMMENDATION_LIMIT:
            page_size = RecommendationDefaults.MAX_RECOMMENDATION_LIMIT

        profile = await self._preference_repository.get_by_user_id(current_user.id)
        if profile is None:
            profile = UserPreferenceProfile(user_id=current_user.id)
            await self._preference_repository.create(profile)

        source_map, category_map, preferred_source_type_ids = (
            await self._load_reference_data(profile)
        )
        now = datetime.now(UTC)

        candidate_limit = RecommendationDefaults.CANDIDATE_LIMIT
        articles = await self._article_repository.list_personalized_feed_story_candidates(
            limit=candidate_limit,
            offset=0,
            muted_company_ids=list(profile.muted_company_ids),
            muted_topic_ids=list(profile.muted_topic_ids),
            muted_category_ids=list(profile.muted_category_ids),
            muted_source_ids=list(profile.muted_source_ids),
            followed_company_ids=list(profile.followed_company_ids),
            followed_topic_ids=list(profile.followed_topic_ids),
            followed_category_ids=list(profile.followed_category_ids),
            preferred_source_type_ids=preferred_source_type_ids,
        )

        cluster_map: dict[UUID | None, list[Article]] = {}
        for article in articles:
            cluster_map.setdefault(article.cluster_id, []).append(article)

        all_cluster_ids = [cid for cid in cluster_map if cid is not None]
        clusters: list[StoryCluster] = []
        if all_cluster_ids:
            clusters = await self._story_cluster_repository.get_by_ids(all_cluster_ids)
        cluster_by_id = {c.id: c for c in clusters}

        activities: list[Any] = []
        if all_cluster_ids:
            activities = await self._story_activity_repository.get_by_cluster_ids(all_cluster_ids)
        activity_by_cluster = {a.story_cluster_id: a for a in activities}

        events_by_cluster: dict[UUID, list[Any]] = {}
        if all_cluster_ids:
            events_by_cluster = await self._story_event_repository.list_by_cluster_ids(
                all_cluster_ids,
                limit=RecommendationDefaults.MAX_EVENTS_PER_CLUSTER,
            )

        trends = await self._trend_repository.list_recent(
            since=now - __import__("datetime").timedelta(days=7),
            limit=200,
        )

        trend_by_cluster = self._match_trends_to_clusters(clusters, trends)

        scored_items: list[
            tuple[ScoredCluster, StoryCluster | None, Article, list[Article] | None, Trend | None, Any | None]
        ] = []

        for cluster_id, cluster_articles in cluster_map.items():
            if cluster_id is None:
                for article in cluster_articles:
                    scored = self._score_standalone_article(article, profile, source_map, now)
                    if scored is not None:
                        scored_items.append((scored, None, article, None, None, None))
                continue

            cluster = cluster_by_id.get(cluster_id)
            if cluster is None:
                for article in cluster_articles:
                    scored = self._score_standalone_article(article, profile, source_map, now)
                    if scored is not None:
                        scored_items.append((scored, None, article, None, None, None))
                continue

            representative = self._pick_representative(cluster, cluster_articles)
            activity = activity_by_cluster.get(cluster_id)
            events = events_by_cluster.get(cluster_id, [])
            trend = trend_by_cluster.get(cluster_id)

            scored = self._engine.score_cluster(
                cluster=cluster,
                representative=representative,
                cluster_articles=cluster_articles,
                profile=profile,
                activity=activity,
                trend=trend,
                events=events,
                source_map=source_map,
                now=now,
            )
            scored_items.append((scored, cluster, representative, cluster_articles, trend, activity))

        scored_trend_items: list[tuple[ScoredCluster, Trend]] = []
        for trend in trends:
            if self._is_trend_muted(trend, profile):
                continue
            scored_trend = self._engine.score_trend(trend, profile, now)
            scored_trend_items.append((scored_trend, trend))

        all_scored = [item[0] for item in scored_items] + [item[0] for item in scored_trend_items]
        all_scored.sort(key=lambda x: (-x.score, x.cluster_id))

        recommendation_limit = page_size * 2
        selected = self._engine.select_diverse(all_scored, recommendation_limit)
        selected = selected[:page_size]

        selected_set = {s.cluster_id for s in selected}
        items = []
        for scored, cluster, representative, cluster_articles, trend, activity in scored_items:  # type: ignore[assignment]
            if scored.cluster_id not in selected_set:
                continue
            items.append(
                self._build_story_response_item(
                    scored,
                    cluster,
                    representative,
                    cluster_articles,
                    trend,
                    category_map,
                    source_map,
                    activity,
                )
            )

        for scored, trend in scored_trend_items:
            if scored.cluster_id not in selected_set:
                continue
            items.append(self._build_trend_response_item(scored, trend))

        items.sort(key=lambda x: (-x.recommendation_score, x.id))

        offset = (page - 1) * page_size
        page_items = items[offset : offset + page_size]

        empty_reason = None
        if not items:
            if (
                not profile.followed_company_ids
                and not profile.followed_topic_ids
                and not profile.followed_category_ids
            ):
                empty_reason = "Configure your interests to see personalized recommendations."
            else:
                empty_reason = "No recommendations found. Try adjusting your filters."

        return RecommendationResponse(
            items=page_items,
            total=len(items),
            limit=page_size,
            offset=offset,
            empty_reason=empty_reason,
        )

    async def _load_reference_data(
        self,
        profile: UserPreferenceProfile,
    ) -> tuple[dict[UUID, Any], dict[UUID, str], list[UUID]]:
        sources = await self._source_repository.list_all()
        categories = await self._category_repository.list_all()
        source_map = {source.id: source for source in sources}
        category_map = {category.id: category.name for category in categories}

        preferred_source_type_ids: list[UUID] = []
        if profile.preferred_source_types:
            for source in sources:
                if source.source_type.value in profile.preferred_source_types:
                    preferred_source_type_ids.append(source.id)

        return source_map, category_map, preferred_source_type_ids

    def _pick_representative(
        self,
        cluster: StoryCluster,
        cluster_articles: list[Article],
    ) -> Article:
        if cluster.representative_article_id is not None:
            for article in cluster_articles:
                if article.id == cluster.representative_article_id:
                    return article
        return max(cluster_articles, key=lambda a: (a.published_at, a.id))

    def _score_standalone_article(
        self,
        article: Article,
        profile: UserPreferenceProfile,
        source_map: dict[UUID, Any],
        now: datetime,
    ) -> ScoredCluster | None:
        from ai_news_digest.application.services.recommendation.constants import (
            RecommendationSignal,
        )

        reasons: list[str] = []
        signals: list[RecommendationSignal] = []
        score = 30.0

        article_company_ids = {str(cid) for cid in article.company_ids}
        article_topic_ids = {str(tid) for tid in article.topic_ids}
        article_category_ids = {str(cid) for cid in article.category_ids}
        if article.category_id:
            article_category_ids.add(str(article.category_id))

        followed_company_strs = {str(cid) for cid in profile.followed_company_ids}
        followed_topic_strs = {str(tid) for tid in profile.followed_topic_ids}
        followed_category_strs = {str(cid) for cid in profile.followed_category_ids}
        followed_source_strs = {str(sid) for sid in profile.followed_source_ids}

        if article_company_ids & followed_company_strs:
            score = max(0.0, min(100.0, score + 12.0))
            reasons.append("Matches followed company")
            signals.append(
                RecommendationSignal(
                    name="preference",
                    raw_value=1.0,
                    contribution=12.0,
                    explanation="Matches followed company",
                )
            )

        if article_topic_ids & followed_topic_strs:
            score = max(0.0, min(100.0, score + 10.0))
            reasons.append("Matches followed topic")
            signals.append(
                RecommendationSignal(
                    name="preference",
                    raw_value=1.0,
                    contribution=10.0,
                    explanation="Matches followed topic",
                )
            )

        if article_category_ids & followed_category_strs:
            score = max(0.0, min(100.0, score + 8.0))
            reasons.append("Matches followed category")
            signals.append(
                RecommendationSignal(
                    name="preference",
                    raw_value=1.0,
                    contribution=8.0,
                    explanation="Matches followed category",
                )
            )

        if followed_source_strs and str(article.source_id) in followed_source_strs:
            score = max(0.0, min(100.0, score + 6.0))
            reasons.append("Matches followed source")
            signals.append(
                RecommendationSignal(
                    name="preference",
                    raw_value=1.0,
                    contribution=6.0,
                    explanation="Matches followed source",
                )
            )

        if (article.importance_score or 0) >= 0.8:
            score = max(0.0, min(100.0, score + 10.0))
            reasons.append("High importance story")
            signals.append(
                RecommendationSignal(
                    name="global_importance",
                    raw_value=article.importance_score or 0,
                    contribution=10.0,
                    explanation="High importance story",
                )
            )

        if article.published_at >= now - __import__("datetime").timedelta(hours=24):
            score = max(0.0, min(100.0, score + 6.0))
            reasons.append("Fresh coverage")
            signals.append(
                RecommendationSignal(
                    name="fresh_coverage",
                    raw_value=1.0,
                    contribution=6.0,
                    explanation="Fresh coverage",
                )
            )

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

        score = max(0.0, min(100.0, score))

        return ScoredCluster(
            cluster_id=str(article.id),
            article_id=str(article.id),
            score=score,
            signals=signals,
            reasons=reasons,
            company_ids=article_company_ids,
            topic_ids=article_topic_ids,
            category_ids=article_category_ids,
            source_id=str(article.source_id) if article.source_id else None,
        )

    def _match_trends_to_clusters(
        self,
        clusters: list[StoryCluster],
        trends: list[Trend],
    ) -> dict[UUID, Trend]:
        trend_by_cluster: dict[UUID, Trend] = {}
        for cluster in clusters:
            for trend in trends:
                if self._trend_matches_cluster(trend, cluster):
                    trend_by_cluster[cluster.id] = trend
                    break
        return trend_by_cluster

    def _trend_matches_cluster(self, trend: Trend, cluster: StoryCluster) -> bool:
        cluster_company_ids = {
            str(cid)
            for a in getattr(cluster, "articles", [])
            for cid in getattr(a, "company_ids", [])
        }
        cluster_topic_ids = {
            str(tid)
            for a in getattr(cluster, "articles", [])
            for tid in getattr(a, "topic_ids", [])
        }
        cluster_category_ids = {
            str(cid)
            for a in getattr(cluster, "articles", [])
            for cid in getattr(a, "category_ids", [])
        }

        if not cluster_company_ids and not cluster_topic_ids and not cluster_category_ids:
            return False

        return bool(
            (trend.related_company_ids & cluster_company_ids)
            or (trend.related_topic_ids & cluster_topic_ids)
            or (trend.related_category_ids & cluster_category_ids)
        )

    def _is_trend_muted(self, trend: Trend, profile: UserPreferenceProfile) -> bool:
        muted_company_strs = {str(cid) for cid in profile.muted_company_ids}
        muted_topic_strs = {str(tid) for tid in profile.muted_topic_ids}
        muted_category_strs = {str(cid) for cid in profile.muted_category_ids}

        if muted_company_strs and trend.related_company_ids & muted_company_strs:
            return True
        if muted_topic_strs and trend.related_topic_ids & muted_topic_strs:
            return True
        return bool(muted_category_strs and trend.related_category_ids & muted_category_strs)

    def _build_story_response_item(
        self,
        scored: ScoredCluster,
        cluster: StoryCluster | None,
        representative: Article,
        cluster_articles: list[Article] | None,
        trend: Trend | None,
        category_map: dict[UUID, str],
        source_map: dict[UUID, Any],
        activity: Any | None = None,
    ) -> RecommendationItemResponse:
        source_name = None
        source_type = None
        if representative.source_id and representative.source_id in source_map:
            source = source_map[representative.source_id]
            source_name = source.name
            source_type = source.source_type.value

        category_name = None
        if representative.category_id and representative.category_id in category_map:
            category_name = category_map[representative.category_id]

        activity_status = None
        activity_score = None
        if activity is not None:
            activity_status = (
                activity.status.value
                if hasattr(activity.status, "value")
                else str(activity.status)
            )
            activity_score = activity.activity_score

        trend_score = None
        momentum_score = None
        if trend:
            trend_score = trend.trend_score
            momentum_score = trend.momentum_score

        companies = list({c for a in (cluster_articles or []) for c in a.companies})
        topics = list({t for a in (cluster_articles or []) for t in a.topics})
        categories = []
        if category_name:
            categories.append(category_name)

        article_count = len(cluster_articles) if cluster_articles else 1
        source_count = len({a.source_id for a in (cluster_articles or [])})

        return RecommendationItemResponse(
            item_type="story",
            id=scored.article_id,
            title=representative.title,
            summary=representative.summary,
            source_name=source_name,
            source_type=source_type,
            published_at=representative.published_at.isoformat()
            if representative.published_at
            else None,
            latest_update_at=cluster.last_updated_at.isoformat()
            if cluster
            else None,
            importance_score=cluster.importance_score
            if cluster
            else representative.importance_score,
            confidence=cluster.confidence if cluster else representative.confidence,
            activity_status=activity_status,
            activity_score=activity_score,
            trend_score=trend_score,
            momentum_score=momentum_score,
            recommendation_score=scored.score,
            recommendation_reasons=scored.reasons,
            companies=companies,
            topics=topics,
            categories=categories,
            cluster_id=scored.cluster_id,
            cluster_slug=cluster.slug if cluster else None,
            article_count=article_count,
            source_count=source_count,
        )

    def _build_trend_response_item(
        self,
        scored: ScoredCluster,
        trend: Trend,
    ) -> RecommendationItemResponse:
        return RecommendationItemResponse(
            item_type="trend",
            id=str(trend.id),
            title=trend.display_name,
            summary=trend.explanation,
            source_name=None,
            source_type=None,
            published_at=trend.first_detected_at.isoformat() if trend.first_detected_at else None,
            latest_update_at=trend.last_detected_at.isoformat() if trend.last_detected_at else None,
            importance_score=None,
            confidence=None,
            activity_status=(
                trend.status.value
                if hasattr(trend.status, "value")
                else str(trend.status)
            ),
            activity_score=None,
            trend_score=trend.trend_score,
            momentum_score=trend.momentum_score,
            recommendation_score=scored.score,
            recommendation_reasons=scored.reasons,
            companies=[str(cid) for cid in trend.related_company_ids],
            topics=[str(tid) for tid in trend.related_topic_ids],
            categories=[str(cid) for cid in trend.related_category_ids],
            cluster_id=None,
            cluster_slug=None,
            article_count=trend.story_count,
            source_count=trend.source_count,
        )


__all__ = ["GetRecommendationsUseCase"]
