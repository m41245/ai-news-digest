from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from ai_news_digest.application.dto.user_preference import (
    FeedSort,
    PersonalizedFeedItemResponse,
    PersonalizedFeedResponse,
)
from ai_news_digest.application.services.ranking.constants import (
    FeedDefaults,
    RankingExplanation,
    RankingWeights,
)
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.category_repository import CategoryRepository
from ai_news_digest.domain.ports.company_repository import CompanyRepository
from ai_news_digest.domain.ports.source_repository import SourceRepository
from ai_news_digest.domain.ports.story_cluster_repository import StoryClusterRepository
from ai_news_digest.domain.ports.user_preference_repository import UserPreferenceRepository


class GetPersonalizedFeedUseCase:
    """Return a deterministic, explainable personalized feed for the current user."""

    def __init__(
        self,
        preference_repository: UserPreferenceRepository,
        article_repository: ArticleRepository,
        story_cluster_repository: StoryClusterRepository,
        source_repository: SourceRepository,
        category_repository: CategoryRepository,
        company_repository: CompanyRepository,
    ) -> None:
        self._preference_repository = preference_repository
        self._article_repository = article_repository
        self._story_cluster_repository = story_cluster_repository
        self._source_repository = source_repository
        self._category_repository = category_repository
        self._company_repository = company_repository

    async def execute(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = FeedDefaults.DEFAULT_PAGE_SIZE,
        sort: FeedSort = FeedDefaults.DEFAULT_SORT,
        min_importance: float | None = None,
        min_confidence: float | None = None,
    ) -> PersonalizedFeedResponse:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = FeedDefaults.DEFAULT_PAGE_SIZE
        if page_size > FeedDefaults.MAX_PAGE_SIZE:
            page_size = FeedDefaults.MAX_PAGE_SIZE

        profile = await self._preference_repository.get_by_user_id(current_user.id)

        if profile is None:
            profile = UserPreferenceProfile(user_id=current_user.id)
            await self._preference_repository.create(profile)

        effective_min_importance = (
            min_importance if min_importance is not None else profile.min_importance
        )
        effective_min_confidence = (
            min_confidence if min_confidence is not None else profile.min_confidence
        )

        source_map, category_map, preferred_source_type_ids = (
            await self._load_reference_data(profile)
        )

        now = datetime.now(UTC)

        candidate_limit = FeedDefaults.CANDIDATE_LIMIT + page_size
        articles = await self._article_repository.list_personalized_feed_story_candidates(
            limit=candidate_limit,
            offset=0,
            min_importance=effective_min_importance,
            min_confidence=effective_min_confidence,
            muted_company_ids=list(profile.muted_company_ids),
            muted_topic_ids=list(profile.muted_topic_ids),
            muted_category_ids=list(profile.muted_category_ids),
            followed_company_ids=list(profile.followed_company_ids),
            followed_topic_ids=list(profile.followed_topic_ids),
            followed_category_ids=list(profile.followed_category_ids),
            preferred_source_type_ids=preferred_source_type_ids,
        )

        filtered = self._apply_freshness_filter(articles, profile, now)

        cluster_map: dict[UUID | None, list[Article]] = {}
        for article in filtered:
            cluster_map.setdefault(article.cluster_id, []).append(article)

        all_cluster_ids = [cid for cid in cluster_map if cid is not None]
        clusters: list[StoryCluster] = []
        if all_cluster_ids:
            for cid in all_cluster_ids:
                cluster = await self._story_cluster_repository.get_by_id(cid)
                if cluster is not None:
                    clusters.append(cluster)
        cluster_by_id = {c.id: c for c in clusters}

        feed_items: list[PersonalizedFeedItemResponse] = []

        for cluster_id, cluster_articles in cluster_map.items():
            if cluster_id is None:
                for article in cluster_articles:
                    explanation = self._score_fallback(article, profile, source_map, now)
                    item = self._build_fallback_item(
                        article, profile, source_map, category_map, explanation, now
                    )
                    feed_items.append(item)
                continue

            cluster = cluster_by_id.get(cluster_id)
            if cluster is None:
                for article in cluster_articles:
                    explanation = self._score_fallback(article, profile, source_map, now)
                    item = self._build_fallback_item(
                        article, profile, source_map, category_map, explanation, now
                    )
                    feed_items.append(item)
                continue

            representative = self._pick_representative(cluster, cluster_articles)
            explanation = self._score_cluster(
                cluster, representative, cluster_articles, profile, source_map, now
            )

            has_correction = any(
                "correction" in (a.title or "").lower()
                or "retraction" in (a.title or "").lower()
                for a in cluster_articles
            )

            has_contradiction = False
            if cluster is not None:
                cluster_titles = [a.title for a in cluster_articles if a.title]
                if len(cluster_titles) >= 2:
                    title_sets = [set(t.lower().split()) for t in cluster_titles]
                    overlap = len(set.intersection(*title_sets)) if title_sets else 0
                    union = len(set.union(*title_sets)) if title_sets else 0
                    if union > 0 and overlap / union < 0.3:
                        has_contradiction = True

            source_name = None
            source_type = None
            if representative.source_id and representative.source_id in source_map:
                source = source_map[representative.source_id]
                source_name = source.name
                source_type = source.source_type.value

            category_name = (
                category_map.get(representative.category_id)
                if representative.category_id
                else None
            )

            feed_items.append(
                PersonalizedFeedItemResponse(
                    id=str(representative.id),
                    title=representative.title,
                    source_name=source_name,
                    source_type=source_type,
                    published_at=representative.published_at.isoformat(),
                    latest_update_at=cluster.last_updated_at.isoformat(),
                    importance_score=cluster.importance_score,
                    confidence=cluster.confidence,
                    companies=list({c for a in cluster_articles for c in a.companies}),
                    topics=list({t for a in cluster_articles for t in a.topics}),
                    categories=list({category_name} if category_name else set()),
                    cluster_id=str(cluster.id),
                    cluster_slug=cluster.slug,
                    article_count=len(cluster_articles),
                    source_count=len({a.source_id for a in cluster_articles}),
                    relevance_reasons=explanation.all_reasons,
                    relevance_score=explanation.score,
                    is_fallback=False,
                    correction_signals=has_correction,
                    contradiction_signals=has_contradiction,
                )
            )

        feed_items = self._sort_items(feed_items, sort)

        total = len(feed_items)
        offset = (page - 1) * page_size
        page_items = feed_items[offset : offset + page_size]

        empty_reason = None
        if (
            total == 0
            and not profile.followed_company_ids
            and not profile.followed_topic_ids
            and not profile.followed_category_ids
        ):
            empty_reason = "Configure your interests to see personalized stories."
        elif total == 0:
            empty_reason = "No matching stories found. Try adjusting your filters."

        return PersonalizedFeedResponse(
            items=page_items,
            total=total,
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

    def _apply_freshness_filter(
        self,
        articles: list[Article],
        profile: UserPreferenceProfile,
        now: datetime,
    ) -> list[Article]:
        if profile.freshness_window_days is None:
            return articles
        cutoff = now - __import__("datetime").timedelta(days=profile.freshness_window_days)
        return [a for a in articles if a.published_at >= cutoff]

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

    def _score_cluster(
        self,
        cluster: StoryCluster,
        representative: Article,
        cluster_articles: list[Article],
        profile: UserPreferenceProfile,
        source_map: dict[UUID, Any],
        now: datetime,
    ) -> RankingExplanation:
        explanation = RankingExplanation()

        article_company_ids = {cid for a in cluster_articles for cid in a.company_ids}
        article_topic_ids = {tid for a in cluster_articles for tid in a.topic_ids}
        article_category_ids = {cid for a in cluster_articles for cid in a.category_ids}
        if representative.category_id:
            article_category_ids.add(representative.category_id)

        if article_company_ids & profile.followed_company_ids:
            explanation.add_personalization("Matches followed company")
            explanation.score += RankingWeights.FOLLOWED_COMPANY

        if article_topic_ids & profile.followed_topic_ids:
            explanation.add_personalization("Matches followed topic")
            explanation.score += RankingWeights.FOLLOWED_TOPIC

        if article_category_ids & profile.followed_category_ids:
            explanation.add_personalization("Matches followed category")
            explanation.score += RankingWeights.FOLLOWED_CATEGORY

        if (cluster.importance_score or 0) >= RankingWeights.HIGH_IMPORTANCE_THRESHOLD:
            explanation.add_quality("High importance", RankingWeights.HIGH_IMPORTANCE)

        source_count = len({a.source_id for a in cluster_articles})
        if source_count >= RankingWeights.MULTIPLE_SOURCES_MIN:
            explanation.add_quality("Multiple independent sources", RankingWeights.MULTIPLE_SOURCES)

        if cluster.last_updated_at >= now - __import__("datetime").timedelta(
            days=RankingWeights.RECENTLY_UPDATED_DAYS
        ):
            explanation.add_freshness("Recently updated story", RankingWeights.RECENTLY_UPDATED)

        if (cluster.confidence or 0) >= RankingWeights.STRONG_CONFIDENCE_THRESHOLD:
            explanation.add_quality("Strong confidence", RankingWeights.STRONG_CONFIDENCE)

        if representative.published_at >= now - __import__("datetime").timedelta(
            hours=RankingWeights.FRESH_COVERAGE_HOURS
        ):
            explanation.add_freshness("Fresh coverage", RankingWeights.FRESH_COVERAGE)

        if profile.preferred_source_types and representative.source_id in source_map:
            source = source_map[representative.source_id]
            if source.source_type.value in profile.preferred_source_types:
                explanation.add_personalization("Preferred source type")
                explanation.score += RankingWeights.PREFERRED_SOURCE_TYPE

        if not explanation.all_reasons:
            explanation.add_fallback("Recent coverage")

        return explanation

    def _score_fallback(
        self,
        article: Article,
        profile: UserPreferenceProfile,
        source_map: dict[UUID, Any],
        now: datetime,
    ) -> RankingExplanation:
        explanation = RankingExplanation()

        article_company_ids = set(article.company_ids)
        article_topic_ids = set(article.topic_ids)
        article_category_ids = set(article.category_ids)
        if article.category_id:
            article_category_ids.add(article.category_id)

        if article_company_ids & profile.followed_company_ids:
            explanation.add_personalization("Matches followed company")
            explanation.score += RankingWeights.FOLLOWED_COMPANY

        if article_topic_ids & profile.followed_topic_ids:
            explanation.add_personalization("Matches followed topic")
            explanation.score += RankingWeights.FOLLOWED_TOPIC

        if article_category_ids & profile.followed_category_ids:
            explanation.add_personalization("Matches followed category")
            explanation.score += RankingWeights.FOLLOWED_CATEGORY

        if (article.importance_score or 0) >= RankingWeights.HIGH_IMPORTANCE_THRESHOLD:
            explanation.add_quality("High importance", RankingWeights.HIGH_IMPORTANCE)

        if (article.confidence or 0) >= RankingWeights.STRONG_CONFIDENCE_THRESHOLD:
            explanation.add_quality("Strong confidence", RankingWeights.STRONG_CONFIDENCE)

        if article.published_at >= now - __import__("datetime").timedelta(
            hours=RankingWeights.FRESH_COVERAGE_HOURS
        ):
            explanation.add_freshness("Fresh coverage", RankingWeights.FRESH_COVERAGE)

        if profile.preferred_source_types and article.source_id in source_map:
            source = source_map[article.source_id]
            if source.source_type.value in profile.preferred_source_types:
                explanation.add_personalization("Preferred source type")
                explanation.score += RankingWeights.PREFERRED_SOURCE_TYPE

        if not explanation.all_reasons:
            explanation.add_fallback("Recent coverage")

        return explanation

    def _build_fallback_item(
        self,
        article: Article,
        profile: UserPreferenceProfile,
        source_map: dict[UUID, Any],
        category_map: dict[UUID, str],
        explanation: RankingExplanation,
        now: datetime,
    ) -> PersonalizedFeedItemResponse:
        source_name = None
        source_type = None
        if article.source_id and article.source_id in source_map:
            source = source_map[article.source_id]
            source_name = source.name
            source_type = source.source_type.value

        category_name = category_map.get(article.category_id) if article.category_id else None

        return PersonalizedFeedItemResponse(
            id=str(article.id),
            title=article.title,
            source_name=source_name,
            source_type=source_type,
            published_at=article.published_at.isoformat(),
            latest_update_at=article.published_at.isoformat(),
            importance_score=article.importance_score,
            confidence=article.confidence,
            companies=list(article.companies),
            topics=list(article.topics),
            categories=list({category_name} if category_name else set()),
            relevance_reasons=explanation.all_reasons,
            relevance_score=explanation.score,
            is_fallback=True,
        )

    def _sort_items(
        self,
        items: list[PersonalizedFeedItemResponse],
        sort: FeedSort,
    ) -> list[PersonalizedFeedItemResponse]:
        if sort == "relevance":
            return sorted(
                items,
                key=lambda item: (
                    -item.relevance_score,
                    -item.importance_score if item.importance_score is not None else 0,
                    item.published_at or "",
                    item.id,
                ),
            )
        if sort == "importance":
            return sorted(
                items,
                key=lambda item: (
                    -(item.importance_score or 0),
                    item.published_at or "",
                    item.id,
                ),
            )
        return sorted(
            items,
            key=lambda item: item.published_at or "",
            reverse=True,
        )
