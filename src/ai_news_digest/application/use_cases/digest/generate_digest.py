from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from ai_news_digest.application.dto.digest_article_view import DigestArticleView
from ai_news_digest.application.services.ranking.story_ranking_service import (
    StoryRankingEngine,
)
from ai_news_digest.application.services.ranking.top_story_selector import (
    TopStorySelector,
)
from ai_news_digest.core.config import Settings, get_settings
from ai_news_digest.core.exceptions import ValidationError
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.category_repository import CategoryRepository
from ai_news_digest.domain.ports.company_repository import CompanyRepository
from ai_news_digest.domain.ports.digest_repository import DigestRepository
from ai_news_digest.domain.ports.source_repository import SourceRepository
from ai_news_digest.domain.ports.story_cluster_repository import StoryClusterRepository
from ai_news_digest.domain.ports.topic_repository import TopicRepository


@dataclass(slots=True)
class DigestGenerationResult:
    """Result returned after creating a digest."""

    digest_id: UUID
    included_articles: int
    generated_at: datetime
    top_story_cluster_id: UUID | None = None
    top_story_score: float | None = None


class GenerateDigestUseCase:
    """Create a digest from digest-eligible articles."""

    def __init__(
        self,
        article_repository: ArticleRepository,
        digest_repository: DigestRepository,
        source_repository: SourceRepository,
        category_repository: CategoryRepository,
        story_cluster_repository: StoryClusterRepository | None = None,
        company_repository: CompanyRepository | None = None,
        topic_repository: TopicRepository | None = None,
    ) -> None:
        self._article_repository = article_repository
        self._digest_repository = digest_repository
        self._source_repository = source_repository
        self._category_repository = category_repository
        self._story_cluster_repository = story_cluster_repository
        self._company_repository = company_repository
        self._topic_repository = topic_repository

    async def execute(
        self,
        *,
        title: str,
        content: str | None = None,
        limit: int | None = None,
    ) -> DigestGenerationResult:
        """Create a digest from eligible articles and persist it."""
        settings = get_settings()
        effective_limit = limit if limit is not None else settings.digest_max_articles
        eligible_articles = await self._article_repository.list_digest_eligible(
            limit=effective_limit,
        )

        if not eligible_articles:
            raise ValidationError("No digest-eligible articles were found.")

        selected_articles = eligible_articles
        selected_ids = [article.id for article in selected_articles]

        if (
            settings.story_ranking_enabled
            and self._company_repository is not None
            and self._topic_repository is not None
        ):
            if self._story_cluster_repository is None:
                raise ValidationError("Story cluster repository is required for ranking.")
            selected_articles = await self._apply_ranking(
                eligible_articles, settings, effective_limit
            )
            selected_ids = [article.id for article in selected_articles]

        if content is None:
            content = await self._build_content(selected_articles)

        digest = Digest.create(
            title=title,
            content=content,
            digest_format=DigestFormat.MARKDOWN,
            article_ids=selected_ids,
        )

        persisted_digest = None
        try:
            persisted_digest = await self._digest_repository.create(digest)

            await self._article_repository.mark_status_bulk(
                selected_ids,
                ArticleStatus.READY,
            )

            await self._digest_repository.commit()
        except Exception:
            if persisted_digest is not None:
                with contextlib.suppress(Exception):
                    await self._digest_repository.rollback()
                with contextlib.suppress(Exception):
                    await self._digest_repository.delete(persisted_digest.id)
            raise

        top_story_cluster_id = None
        top_story_score = None
        if (
            settings.story_ranking_enabled
            and self._story_cluster_repository is not None
            and self._company_repository is not None
            and self._topic_repository is not None
        ):
            top_story_cluster_id, top_story_score = await self._compute_top_story()

        return DigestGenerationResult(
            digest_id=persisted_digest.id,
            included_articles=len(selected_ids),
            generated_at=persisted_digest.generated_at,
            top_story_cluster_id=top_story_cluster_id,
            top_story_score=top_story_score,
        )

    async def _apply_ranking(
        self,
        eligible_articles: list[Article],
        settings: Settings,
        effective_limit: int,
    ) -> list[Article]:
        """Apply story cluster ranking to select articles."""
        if self._story_cluster_repository is None:
            raise ValidationError("Story cluster repository is required for ranking.")
        if self._company_repository is None:
            raise ValidationError("Company repository is required for ranking.")
        if self._topic_repository is None:
            raise ValidationError("Topic repository is required for ranking.")

        cluster_map: dict[UUID, list[Article]] = {}
        for article in eligible_articles:
            if article.cluster_id is not None:
                cluster_map.setdefault(article.cluster_id, []).append(article)

        cluster_ids = list(cluster_map.keys())
        clusters: list[StoryCluster] = []
        if cluster_ids:
            for cid in cluster_ids:
                cluster = await self._story_cluster_repository.get_by_id(cid)
                if cluster is not None:
                    clusters.append(cluster)

        if not clusters:
            return eligible_articles

        source_map_raw = await self._source_repository.list_all()
        source_map = {str(s.id): s for s in source_map_raw}

        category_map_raw = await self._category_repository.list_all()
        known_category_ids = {str(c.id) for c in category_map_raw}

        company_map_raw = await self._company_repository.list_all()
        known_company_ids = {str(c.id) for c in company_map_raw}

        topic_map_raw = await self._topic_repository.list_all()
        known_topic_ids = {str(t.id) for t in topic_map_raw}

        engine = StoryRankingEngine(
            recency_weight=settings.ranking_recency_weight,
            source_trust_weight=settings.ranking_source_trust_weight,
            source_diversity_weight=settings.ranking_source_diversity_weight,
            corroboration_weight=settings.ranking_corroboration_weight,
            company_relevance_weight=settings.ranking_company_relevance_weight,
            category_topic_relevance_weight=settings.ranking_category_topic_relevance_weight,
            article_quality_weight=settings.ranking_article_quality_weight,
            official_announcement_weight=settings.ranking_official_announcement_weight,
            recency_decay_hours=settings.ranking_recency_decay_hours,
        )

        selector = TopStorySelector(ranking_engine=engine)
        ranked_clusters, _ = selector.rank_and_select(
            clusters=clusters,
            cluster_articles={str(cid): articles for cid, articles in cluster_map.items()},
            source_map=source_map,
            known_company_ids=known_company_ids,
            known_topic_ids=known_topic_ids,
            known_category_ids=known_category_ids,
        )

        updates = []
        for ranked in ranked_clusters:
            explanation_parts = [s.explanation for s in ranked.signals if s.explanation]
            explanation = "; ".join(explanation_parts) if explanation_parts else ""
            updates.append((ranked.cluster.id, ranked.score, explanation))

        if updates:
            await self._story_cluster_repository.bulk_update_ranking(updates)

        unclustered = [a for a in eligible_articles if a.cluster_id is None]
        clustered_by_cluster: dict[UUID, list[Article]] = {}
        for cid, articles in cluster_map.items():
            clustered_by_cluster[cid] = articles

        selected: list[Article] = []
        for ranked in ranked_clusters:
            cid = ranked.cluster.id
            if cid in clustered_by_cluster:
                selected.extend(clustered_by_cluster[cid])
        selected.extend(unclustered)

        return selected[:effective_limit]

    async def _compute_top_story(self) -> tuple[UUID | None, float | None]:
        """Compute the top story from recent active clusters."""
        settings = get_settings()
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=settings.ranking_lookback_hours)

        if self._story_cluster_repository is None:
            raise ValidationError("Story cluster repository is required for top story.")
        if self._company_repository is None:
            raise ValidationError("Company repository is required for top story.")
        if self._topic_repository is None:
            raise ValidationError("Topic repository is required for top story.")

        clusters = await self._story_cluster_repository.find_recent_active_clusters(
            cutoff=cutoff,
            limit=settings.ranking_max_candidates,
        )

        if not clusters:
            return None, None

        source_map_raw = await self._source_repository.list_all()
        source_map = {str(s.id): s for s in source_map_raw}

        category_map_raw = await self._category_repository.list_all()
        known_category_ids = {str(c.id) for c in category_map_raw}

        company_map_raw = await self._company_repository.list_all()
        known_company_ids = {str(c.id) for c in company_map_raw}

        topic_map_raw = await self._topic_repository.list_all()
        known_topic_ids = {str(t.id) for t in topic_map_raw}

        engine = StoryRankingEngine(
            recency_weight=settings.ranking_recency_weight,
            source_trust_weight=settings.ranking_source_trust_weight,
            source_diversity_weight=settings.ranking_source_diversity_weight,
            corroboration_weight=settings.ranking_corroboration_weight,
            company_relevance_weight=settings.ranking_company_relevance_weight,
            category_topic_relevance_weight=settings.ranking_category_topic_relevance_weight,
            article_quality_weight=settings.ranking_article_quality_weight,
            official_announcement_weight=settings.ranking_official_announcement_weight,
            recency_decay_hours=settings.ranking_recency_decay_hours,
        )

        cluster_articles: dict[str, list[Article]] = {}
        for cluster in clusters:
            articles = await self._article_repository.list_by_cluster_id(cluster.id)
            cluster_articles[str(cluster.id)] = articles

        selector = TopStorySelector(ranking_engine=engine)
        _, top_story = selector.rank_and_select(
            clusters=clusters,
            cluster_articles=cluster_articles,
            source_map=source_map,
            known_company_ids=known_company_ids,
            known_topic_ids=known_topic_ids,
            known_category_ids=known_category_ids,
        )

        if top_story.top_story_cluster_id is not None:
            return UUID(top_story.top_story_cluster_id), top_story.top_story_score

        return None, None

    async def _build_content(self, articles: list[Article]) -> str:
        """
        Build structured Markdown digest content from selected articles.
        """
        from ai_news_digest.application.digest.digest_builder import DigestBuilder

        sources = await self._source_repository.list_all()
        source_map = {source.id: source.name for source in sources}

        categories = await self._category_repository.list_all()
        category_map = {category.id: category.name for category in categories}

        views = []
        for article in articles:
            source_name = source_map.get(article.source_id, "Unknown Source")
            category_name = category_map.get(article.category_id) if article.category_id else None

            views.append(
                DigestArticleView(
                    article_id=article.id,
                    title=article.title,
                    url=article.url,
                    summary=article.summary,
                    source_name=source_name,
                    category_name=category_name,
                    published_at=article.published_at,
                )
            )

        builder = DigestBuilder()
        return builder.build(
            title="",
            generated_at=datetime.now(UTC),
            articles=views,
        )
