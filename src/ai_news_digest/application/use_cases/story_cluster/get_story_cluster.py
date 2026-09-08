from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from ai_news_digest.application.dto.story_cluster import (
    StoryClusterArticleResponse,
    StoryClusterDetailResponse,
)
from ai_news_digest.application.exceptions.story_cluster import (
    StoryClusterNotFoundError,
)
from ai_news_digest.application.use_cases.story_cluster.story_intelligence import (
    TimelineItem,
    build_timeline,
    classify_source_role,
    compute_what_changed,
    compute_what_changed_with_evidence,
    detect_signals,
)

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.article_repository import ArticleRepository
    from ai_news_digest.domain.ports.source_repository import SourceRepository
    from ai_news_digest.domain.ports.story_cluster_repository import (
        StoryClusterRepository,
    )


class GetStoryClusterUseCase:
    """
    Application use case responsible for retrieving a story cluster by slug.
    """

    def __init__(
        self,
        cluster_repository: StoryClusterRepository,
        article_repository: ArticleRepository,
        source_repository: SourceRepository,
    ) -> None:
        self._cluster_repository = cluster_repository
        self._article_repository = article_repository
        self._source_repository = source_repository

    async def execute(
        self,
        slug: str,
    ) -> StoryClusterDetailResponse:
        """
        Retrieve a story cluster by its slug, including its recent articles,
        a chronological timeline, source-role labels, and detected changes.
        """

        cluster = await self._cluster_repository.get_by_slug(slug)

        if cluster is None:
            raise StoryClusterNotFoundError(slug)

        articles = await self._article_repository.list_by_cluster_id(
            cluster_id=cluster.id,
            limit=100,
        )

        sources = await self._source_repository.list_all()
        source_map = {source.id: source.name for source in sources}
        source_type_map = {source.id: source.source_type.value for source in sources}

        representative_article = None
        if cluster.representative_article_id is not None:
            for article in articles:
                if article.id == cluster.representative_article_id:
                    representative_article = article
                    break

        source_role_map: dict[str, str] = {}
        for article in articles:
            source_type = source_type_map.get(article.source_id, "other")
            source_role = classify_source_role(
                article_published_at=article.published_at,
                cluster_first_published_at=cluster.first_published_at,
                source_type=source_type,
                representative_title=(
                    representative_article.title if representative_article else None
                ),
                article_title=article.title,
            )
            source_role_map[str(article.id)] = source_role

        article_count = len(articles)
        unique_source_ids = {article.source_id for article in articles}
        source_count = len(unique_source_ids)
        latest_article_id = str(articles[0].id) if articles else None

        recent_articles = [
            StoryClusterArticleResponse(
                id=str(article.id),
                title=article.title,
                url=article.url,
                summary=article.summary,
                published_at=article.published_at.isoformat(),
                importance_score=article.importance_score,
                confidence=article.confidence,
                source_name=source_map.get(article.source_id),
                source_type=source_type_map.get(article.source_id),
                source_role=source_role_map.get(str(article.id)),
            )
            for article in articles[:20]
        ]

        timeline = build_timeline(articles, source_map)
        for item in timeline:
            item["source_role"] = source_role_map.get(item["id"])

        typed_timeline: list[TimelineItem] = cast(list[TimelineItem], timeline)

        what_changed = compute_what_changed(timeline)
        what_changed_evidence = [
            item.to_dict()
            for item in compute_what_changed_with_evidence(
                typed_timeline,
                detected_at=datetime.now(UTC).isoformat(),
            )
        ]

        # Add per-timeline-item confidence so the frontend can render it.
        from ai_news_digest.application.evaluation.confidence import (
            compute_evidence_strength,
            compute_source_role_confidence,
        )

        for item in timeline:
            signals = detect_signals(item.get("title"))
            item["signals"] = signals
            item["source_role_confidence"] = compute_source_role_confidence(
                has_source_type=bool(item.get("source_type")),
                has_representative_title=bool(
                    representative_article and representative_article.title
                ),
                is_correction_signal=signals["is_correction"] or signals["is_retraction"],
                is_background_signal=signals["is_background"],
                is_primary_window=(item.get("source_type") == "official_company"),
                is_tech_or_business_window=item.get("source_type")
                in {"tech_publication", "business_news"},
            ).value
            item["evidence_confidence"] = compute_evidence_strength(
                supporting_article_count=1,
                distinct_source_count=1,
                fields_used=["title", "summary"],
            ).value

        contradictions: list[dict[str, object]] = []
        needs_verification = False
        try:
            from ai_news_digest.application.evaluation.contradiction import (
                detect_contradictions,
            )

            detected = detect_contradictions(typed_timeline)
            contradictions = [c.to_dict() for c in detected]
            needs_verification = any(c.needs_verification for c in detected)
        except Exception:
            # Contradiction detection is a best-effort, additive feature.
            # Failures must never break the cluster detail page.
            contradictions = []
            needs_verification = False

        # Cluster-level intelligence confidence.
        from ai_news_digest.application.evaluation.confidence import (
            Confidence,
            aggregate_article_confidence,
            compute_cluster_confidence,
        )

        cluster_confidence = compute_cluster_confidence(
            article_count=article_count,
            unique_source_count=source_count,
            average_article_confidence=aggregate_article_confidence(typed_timeline),
        )

        return StoryClusterDetailResponse(
            id=str(cluster.id),
            title=cluster.title,
            slug=cluster.slug,
            summary=cluster.summary,
            first_published_at=cluster.first_published_at.isoformat(),
            last_updated_at=cluster.last_updated_at.isoformat(),
            representative_article_id=str(cluster.representative_article_id)
            if cluster.representative_article_id is not None
            else None,
            latest_article_id=latest_article_id,
            importance_score=cluster.importance_score,
            confidence=cluster.confidence,
            status=cluster.status.value,
            article_count=article_count,
            source_count=source_count,
            recent_articles=recent_articles,
            timeline=timeline,
            what_changed=what_changed,
            what_changed_evidence=what_changed_evidence,
            contradictions=contradictions,
            needs_verification=needs_verification,
            intelligence_confidence=(
                cluster_confidence.value
                if isinstance(cluster_confidence, Confidence)
                else cluster_confidence
            ),
        )
