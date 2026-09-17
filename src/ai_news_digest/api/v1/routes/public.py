"""
Public, unauthenticated API endpoints.

These routes expose a read-only, enriched view of articles, digests and
categories for the public product experience. No authentication is required.
Only processed articles (beyond NEW/FAILED) are surfaced.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes._graph_utils import build_graph_name_map
from ai_news_digest.api.v1.routes.timeline import router as timeline_router
from ai_news_digest.api.v1.schemas.common import (
    DEFAULT_PAGE_LIMIT,
    MAX_OFFSET,
    MAX_PAGE_LIMIT,
    PaginatedResponse,
)
from ai_news_digest.api.v1.schemas.public import (
    PublicArticleResponse,
    PublicCategoryResponse,
    PublicClaimResponse,
    PublicCompanyResponse,
    PublicConflictResponse,
    PublicDigestResponse,
    PublicEvidenceResponse,
    PublicStoryClusterResponse,
    PublicStoryClusterSearchResponse,
    PublicTopicResponse,
    PublicTopStoryResponse,
    PublicTrendResponse,
    PublicTrendSearchResponse,
    RelatedStoryResponse,
)
from ai_news_digest.api.v1.schemas.source import SourceResponse
from ai_news_digest.api.v1.schemas.story_intelligence_brief import (
    StoryIntelligenceBriefResponse,
)
from ai_news_digest.application.services.ranking.story_ranking_service import (
    StoryRankingEngine,
)
from ai_news_digest.application.services.ranking.top_story_selector import (
    TopStorySelector,
)
from ai_news_digest.application.services.story_intelligence_brief import (
    StoryIntelligenceBriefService,
)
from ai_news_digest.application.use_cases.story_cluster.story_intelligence import (
    TimelineItem,
    build_timeline,
    classify_source_role,
    compute_what_changed,
    compute_what_changed_with_evidence,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.digest import Digest

logger = get_logger(__name__)

router = APIRouter(
    prefix="/public",
    tags=["Public"],
)


@lru_cache(maxsize=1)
def _cached_source_category_maps(
    sources_tuple: tuple[tuple[str, str], ...],
    categories_tuple: tuple[tuple[str, str], ...],
) -> tuple[dict[str, str], dict[str, str]]:
    source_map = dict(sources_tuple)
    category_map = dict(categories_tuple)
    return source_map, category_map


async def _build_source_and_category_maps(
    container: Container,
) -> tuple[dict[str, str], dict[str, str]]:
    """Build id -> name lookup maps for sources and categories."""
    sources = await container.source_repository.list_all()
    categories = await container.category_repository.list_all()

    sources_tuple = tuple((str(s.id), s.name) for s in sources)
    categories_tuple = tuple((str(c.id), c.name) for c in categories)
    return _cached_source_category_maps(sources_tuple, categories_tuple)


def _to_public_article(
    article: Article,
    source_map: dict[str, str],
    category_map: dict[str, str],
    claims: list[Any] | None = None,
) -> PublicArticleResponse:
    claim_responses = None
    if claims:
        claim_responses = [
            PublicClaimResponse(
                claim=c.claim_text,
                type=c.claim_type.value,
                confidence=c.confidence,
                status=c.status.value,
                evidence_support_score=c.evidence_support_score,
                provenance_source=(
                    c.ai_provider or (c.ai_model and "ai_extracted")
                ) or "deterministic",
                schema_version=c.schema_version,
                prompt_version=c.prompt_version,
                evidence=[
                    PublicEvidenceResponse(
                        evidence_type=ev.evidence_type.value,
                        excerpt=ev.excerpt,
                        source_location=ev.source_location,
                        strength=ev.strength.value if ev.strength else None,
                        article_title=None,
                        source_name=(
                            source_map.get(str(article.source_id))
                            if article.source_id
                            else None
                        ),
                        published_at=(
                            article.published_at.isoformat()
                            if article.published_at
                            else None
                        ),
                    )
                    for ev in (evidence_items or [])
                ] if (evidence_items := getattr(c, 'evidence_items', None)) else None,
            )
            for c in claims
        ]

    ai_provider = getattr(article, "ai_provider", None)
    ai_model = getattr(article, "ai_model", None)
    provenance_source = (
        "ai_extracted" if ai_provider or ai_model else "deterministic"
    )

    return PublicArticleResponse(
        id=str(article.id),
        title=article.title,
        url=article.url,
        summary=article.summary,
        status=article.status.value,
        published_at=article.published_at.isoformat(),
        source_name=source_map.get(str(article.source_id)) if article.source_id else None,
        category_name=(category_map.get(str(article.category_id)) if article.category_id else None),
        companies=list(article.companies) if article.companies else None,
        topics=list(article.topics) if article.topics else None,
        key_takeaways=list(article.key_takeaways) if article.key_takeaways else None,
        why_it_matters=article.why_it_matters,
        importance_score=article.importance_score,
        confidence=article.confidence,
        claims=claim_responses,
        provenance_source=provenance_source,
        extraction_quality=(
            getattr(article, "extraction_quality", None).value  # type: ignore[union-attr]
            if hasattr(getattr(article, "extraction_quality", None), "value")
            else str(getattr(article, "extraction_quality", None))
        ),
        ai_provider=ai_provider,
        ai_model=ai_model,
        ai_processed_at=(
            getattr(article, "ai_processed_at", None).isoformat()  # type: ignore[union-attr]
            if getattr(article, "ai_processed_at", None)
            else None
        ),
    )


@router.get(
    "/articles",
    response_model=PaginatedResponse[PublicArticleResponse],
    summary="List public articles",
)
async def list_public_articles(
    container: Annotated[Container, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
    category_id: Annotated[str | None, Query()] = None,
    source_id: Annotated[str | None, Query()] = None,
    company_id: Annotated[str | None, Query()] = None,
    topic_id: Annotated[str | None, Query()] = None,
    min_importance: Annotated[float | None, Query(ge=0)] = None,
    published_from: Annotated[str | None, Query()] = None,
    published_to: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    mode: Annotated[str | None, Query(pattern="^(lexical|semantic|hybrid)$")] = None,
) -> PaginatedResponse[PublicArticleResponse]:
    """List publicly visible articles with optional filtering and search."""
    settings = get_settings()
    search_mode = mode or "lexical"
    cat_id = UUID(category_id) if category_id else None
    src_id = UUID(source_id) if source_id else None
    comp_id = UUID(company_id) if company_id else None
    topic_uuid = UUID(topic_id) if topic_id else None

    published_from_dt: datetime | None = None
    published_to_dt: datetime | None = None
    if published_from:
        with contextlib.suppress(ValueError):
            published_from_dt = datetime.fromisoformat(published_from)
    if published_to:
        with contextlib.suppress(ValueError):
            published_to_dt = datetime.fromisoformat(published_to)

    source_map, category_map = await _build_source_and_category_maps(container)

    articles = await container.article_repository.list_public_articles(
        limit=limit,
        offset=offset,
        category_id=cat_id,
        source_id=src_id,
        company_id=comp_id,
        topic_id=topic_uuid,
        min_importance=min_importance,
        published_from=published_from_dt,
        published_to=published_to_dt,
        search=search if search_mode != "semantic" else None,
    )

    total = await container.article_repository.count_public_articles(
        category_id=cat_id,
        source_id=src_id,
        company_id=comp_id,
        topic_id=topic_uuid,
        min_importance=min_importance,
        published_from=published_from_dt,
        published_to=published_to_dt,
        search=search if search_mode != "semantic" else None,
    )

    claim_map: dict[str, list[Any]] = {}
    article_ids = [a.id for a in articles]
    if article_ids:
        claim_repo = container.claim_repository
        for aid in article_ids:
            try:
                claim_map[str(aid)] = await claim_repo.list_by_article_id(aid)
            except Exception:
                claim_map[str(aid)] = []

    if (
        search_mode in ("semantic", "hybrid")
        and search
        and settings.semantic_search_enabled
        and container.embedding_service.is_available
    ):
        if len(search) > settings.semantic_search_query_max_length:
            search = search[: settings.semantic_search_query_max_length]

        try:
            from ai_news_digest.domain.models.semantic_document import (
                SemanticDocument,
            )

            query_doc = SemanticDocument(
                id=UUID("00000000-0000-0000-0000-000000000000"),
                title=search,
            )
            query_emb = await container.embedding_service.generate(query_doc)
            semantic_service = container.semantic_search_service
            candidates = articles[: settings.semantic_candidate_limit]
            scored = await semantic_service.search_articles(
                query=search,
                candidates=candidates,
                query_embedding=query_emb.embedding,
            )
            scored_map = {s.article.id: s for s in scored}

            def _combined_score(article: Article) -> float:
                scored_item = scored_map.get(article.id)
                if scored_item is None:
                    return 0.0
                return float(scored_item.combined_score)

            articles = sorted(
                articles,
                key=_combined_score,
                reverse=True,
            )
        except Exception:
            logger.warning(
                "semantic_search.failed",
                error="Semantic search enhancement failed",
            )

    return PaginatedResponse(
        items=[
            _to_public_article(
                a,
                source_map,
                category_map,
                claims=claim_map.get(str(a.id)),
            )
            for a in articles
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/articles/{article_id}/related",
    response_model=list[RelatedStoryResponse],
    summary="Get related stories for an article",
)
async def get_related_stories(
    article_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[RelatedStoryResponse]:
    """Return semantically related story clusters for a given article."""
    article = await container.article_repository.get_public_article(article_id)
    if article is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Article {article_id} not found.")

    cutoff = datetime.now(UTC) - timedelta(hours=72)
    clusters = await container.story_cluster_repository.find_recent_active_clusters(
        cutoff=cutoff,
        limit=200,
    )

    existing_cluster_id = (
        str(article.cluster_id) if article.cluster_id is not None else None
    )

    related = await container.related_story_finder.find_for_article(
        article=article,
        existing_cluster_id=existing_cluster_id,
        clusters=clusters,
        limit=limit,
    )

    graph_signals_map: dict[str, dict[str, Any]] = {}
    if get_settings().knowledge_graph_enabled:
        try:
            from ai_news_digest.application.services.graph_intelligence.graph_intelligence_service import (  # noqa: E501
                GraphIntelligenceService,
            )

            service = GraphIntelligenceService()
            source_company_ids = set(article.companies or [])
            source_topic_ids = set(article.topics or [])
            source_category_ids = set()
            if article.category_id:
                source_category_ids.add(str(article.category_id))

            for cluster in clusters:
                if str(cluster.id) == existing_cluster_id:
                    continue
                candidate_rels = await container.relationship_repository.list_for_entity(
                    entity_type="story",
                    entity_id=cluster.id,
                    status=None,
                    limit=50,
                )
                source_rels = await container.relationship_repository.list_for_entity(
                    entity_type="story",
                    entity_id=article.cluster_id if article.cluster_id else article.id,
                    status=None,
                    limit=50,
                )

                candidate_company_ids = {
                    str(r.object_entity_id)
                    for r in candidate_rels
                    if r.object_entity_type.value == "company"
                }
                candidate_topic_ids = {
                    str(r.object_entity_id)
                    for r in candidate_rels
                    if r.object_entity_type.value == "topic"
                }

                signal = service.compute_related_story_signals(
                    source_cluster_id=str(article.cluster_id or article.id),
                    candidate_cluster_id=str(cluster.id),
                    source_company_ids=source_company_ids,
                    source_topic_ids=source_topic_ids,
                    source_category_ids=source_category_ids,
                    candidate_company_ids=candidate_company_ids,
                    candidate_topic_ids=candidate_topic_ids,
                    candidate_category_ids=set(),
                    relationships=source_rels + candidate_rels,
                )
                if signal:
                    graph_signals_map[str(cluster.id)] = {
                        "graph_score": signal.graph_score,
                        "signals": signal.signals,
                        "explanation": signal.explanation,
                        "relationship_count": signal.relationship_count,
                    }
        except Exception:
            graph_signals_map = {}

    results: list[RelatedStoryResponse] = []
    for r in related:
        graph_data = graph_signals_map.get(r.cluster_id)
        reason = r.reason
        if graph_data and graph_data.get("graph_score", 0) > 0:
            reason = f"{r.reason}; {graph_data['explanation']}"

        results.append(
            RelatedStoryResponse(
                cluster_id=r.cluster_id,
                title=r.title,
                summary=r.summary,
                similarity=r.similarity,
                article_count=r.article_count,
                source_count=r.source_count,
                reason=reason,
            )
        )
        if len(results) >= limit:
            break

    return results


@router.get(
    "/articles/{article_id}",
    response_model=PublicArticleResponse,
    summary="Get a public article",
)
async def get_public_article(
    article_id: UUID,
    container: Annotated[Container, Depends(get_container)],
) -> PublicArticleResponse:
    """Retrieve a single public article by ID."""
    article = await container.article_repository.get_public_article(article_id)

    if article is None:
        raise ResourceNotFoundError(f"Article {article_id} not found.")

    source_map, category_map = await _build_source_and_category_maps(container)

    claims: list[Any] = []
    try:
        claims = await container.claim_repository.list_by_article_id(article_id)
    except Exception:
        claims = []

    return _to_public_article(article, source_map, category_map, claims=claims)


async def _build_top_story(
    digest: Digest,
    container: Container,
) -> dict[str, Any] | None:
    """Build a lightweight top-story payload from the digest's top_story_cluster_id."""
    if not digest.top_story_cluster_id:
        return None

    cluster = await container.story_cluster_repository.get_by_id(digest.top_story_cluster_id)
    if cluster is None:
        return None

    return {
        "cluster_id": str(cluster.id),
        "title": cluster.title,
        "slug": cluster.slug,
        "summary": cluster.summary,
        "importance_score": cluster.importance_score,
        "confidence": cluster.confidence,
        "ranking_score": cluster.ranking_score,
        "ranking_explanation": cluster.ranking_explanation,
    }


@router.get(
    "/digests",
    response_model=PaginatedResponse[PublicDigestResponse],
    summary="List public digests",
)
async def list_public_digests(
    container: Annotated[Container, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
) -> PaginatedResponse[PublicDigestResponse]:
    """List publicly visible digests with pagination."""
    digests = await container.digest_repository.list_recent(limit=limit, offset=offset)
    total = await container.digest_repository.count()

    top_story_map: dict[str, dict[str, Any]] = {}
    cluster_ids = [digest.top_story_cluster_id for digest in digests if digest.top_story_cluster_id]
    if cluster_ids:
        clusters = await asyncio.gather(
            *[container.story_cluster_repository.get_by_id(cid) for cid in cluster_ids]
        )
        for cluster in clusters:
            if cluster is None:
                continue
            cluster_data = {
                "cluster_id": str(cluster.id),
                "title": cluster.title,
                "slug": cluster.slug,
                "summary": cluster.summary,
                "importance_score": cluster.importance_score,
                "confidence": cluster.confidence,
                "ranking_score": cluster.ranking_score,
                "ranking_explanation": cluster.ranking_explanation,
            }
            for digest in digests:
                if digest.top_story_cluster_id == cluster.id:
                    top_story_map[str(digest.id)] = cluster_data

    return PaginatedResponse(
        items=[
            PublicDigestResponse(
                id=str(digest.id),
                title=digest.title,
                content=digest.content,
                format=digest.format.value,
                generated_at=digest.generated_at.isoformat(),
                article_count=len(digest.article_ids),
                top_story_cluster_id=(
                    str(digest.top_story_cluster_id) if digest.top_story_cluster_id else None
                ),
                generation_method=digest.generation_method,
                stories=digest.stories or None,
                top_story=top_story_map.get(str(digest.id)),
            )
            for digest in digests
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/digests/{digest_id}",
    response_model=PublicDigestResponse,
    summary="Get a public digest",
)
async def get_public_digest(
    digest_id: UUID,
    container: Annotated[Container, Depends(get_container)],
) -> PublicDigestResponse:
    """Retrieve a single public digest by ID."""
    digest = await container.digest_repository.get_by_id(digest_id)

    if digest is None:
        raise ResourceNotFoundError(f"Digest {digest_id} not found.")

    top_story = await _build_top_story(digest, container)

    return PublicDigestResponse(
        id=str(digest.id),
        title=digest.title,
        content=digest.content,
        format=digest.format.value,
        generated_at=digest.generated_at.isoformat(),
        article_count=len(digest.article_ids),
        top_story_cluster_id=(
            str(digest.top_story_cluster_id) if digest.top_story_cluster_id else None
        ),
        generation_method=digest.generation_method,
        stories=digest.stories or None,
        top_story=top_story,
    )


@router.get(
    "/story-ranking/top-story",
    response_model=PublicTopStoryResponse,
    summary="Get the current public Top Story",
)
async def get_public_top_story(
    container: Annotated[Container, Depends(get_container)],
) -> PublicTopStoryResponse:
    """Return the highest-ranked eligible StoryCluster for public consumption."""
    settings = get_settings()
    if not settings.story_ranking_enabled:
        return PublicTopStoryResponse(
            generated_at=datetime.now(UTC).isoformat(),
        )

    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=settings.ranking_lookback_hours)

    clusters = await container.story_cluster_repository.find_recent_active_clusters(
        cutoff=cutoff,
        limit=settings.ranking_max_candidates,
    )

    if not clusters:
        return PublicTopStoryResponse(
            total_candidates=0,
            eligible_candidates=0,
            ranking_window_start=cutoff.isoformat(),
            ranking_window_end=now.isoformat(),
            generated_at=now.isoformat(),
        )

    source_map_raw = await container.source_repository.list_all()
    source_map = {str(s.id): s for s in source_map_raw}

    category_map_raw = await container.category_repository.list_all()
    known_category_ids = {str(c.id) for c in category_map_raw}

    company_map_raw = await container.company_repository.list_all()
    known_company_ids = {str(c.id) for c in company_map_raw}

    topic_map_raw = await container.topic_repository.list_all()
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
        articles = await container.article_repository.list_by_cluster_id(cluster.id)
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

    top_cluster = None
    if top_story.top_story_cluster_id:
        top_cluster = await container.story_cluster_repository.get_by_id(
            UUID(top_story.top_story_cluster_id)
        )

    activity_status = None
    activity_score = None
    if top_cluster is not None:
        try:
            activity = await container.story_activity_repository.get_by_story_cluster_id(
                top_cluster.id
            )
            if activity is not None:
                activity_status = activity.status.value
                activity_score = activity.activity_score
        except Exception:  # noqa: S110
            pass

    return PublicTopStoryResponse(
        top_story_cluster_id=top_story.top_story_cluster_id,
        top_story_score=top_story.top_story_score,
        total_candidates=top_story.total_candidates,
        eligible_candidates=top_story.eligible_candidates,
        ranking_window_start=top_story.ranking_window_start.isoformat(),
        ranking_window_end=top_story.ranking_window_end.isoformat(),
        generated_at=top_story.generated_at.isoformat(),
        title=top_cluster.title if top_cluster else None,
        slug=top_cluster.slug if top_cluster else None,
        summary=top_cluster.summary if top_cluster else None,
        importance_score=top_cluster.importance_score if top_cluster else None,
        confidence=top_cluster.confidence if top_cluster else None,
        activity_status=activity_status,
        activity_score=activity_score,
    )


@router.get(
    "/story-clusters/{slug}/brief",
    response_model=StoryIntelligenceBriefResponse,
    summary="Get a story intelligence brief",
)
async def get_story_intelligence_brief(
    slug: str,
    container: Annotated[Container, Depends(get_container)],
) -> StoryIntelligenceBriefResponse:
    """Retrieve a structured intelligence brief for a public story cluster.

    The brief assembles existing M67-M94 intelligence into a coherent
    evidence-first experience without requiring new AI calls.
    """
    settings = get_settings()
    service = StoryIntelligenceBriefService(container=container)

    cache_key = f"story-brief:{slug}"
    cached_brief = None
    with contextlib.suppress(Exception):
        cached_brief = await container.cache_store.get(cache_key)

    if cached_brief is not None:
        brief = cached_brief
    else:
        brief = await service.build_brief(slug=slug)
        if brief:
            with contextlib.suppress(Exception):
                await container.cache_store.set(cache_key, brief, ttl=300)

    if not brief:
        raise ResourceNotFoundError(f"Story cluster with slug '{slug}' not found.")

    quality = brief.get("quality") or {}
    health_status = quality.get("health_status", "insufficient_data")

    if settings.quality_gates_enabled and health_status == "blocked":
        from fastapi import HTTPException
        raise HTTPException(
            status_code=403,
            detail="Intelligence for this story is currently blocked by quality gates.",
        )

    if settings.quality_gates_enabled and quality.get("degraded"):
        degraded_message = (
            "Some intelligence for this story is currently unavailable."
        )
        if quality.get("degraded_message"):
            degraded_message = quality["degraded_message"]
        quality["degraded"] = True
        quality["degraded_message"] = degraded_message
        brief["quality"] = quality

    return StoryIntelligenceBriefResponse(**brief)


@router.get(
    "/story-clusters/{slug}",
    response_model=PublicStoryClusterResponse,
    summary="Get a public story cluster",
)
async def get_public_story_cluster(
    slug: str,
    container: Annotated[Container, Depends(get_container)],
) -> PublicStoryClusterResponse:
    """Retrieve a public story cluster by slug with its recent articles and timeline."""
    cluster = await container.story_cluster_repository.get_by_slug(slug)

    if cluster is None:
        raise ResourceNotFoundError(f"Story cluster with slug '{slug}' not found.")

    articles = await container.article_repository.list_by_cluster_id(
        cluster_id=cluster.id,
        limit=100,
    )

    sources = await container.source_repository.list_all()
    source_map = {str(source.id): source.name for source in sources}
    source_type_map = {str(source.id): source.source_type.value for source in sources}

    representative_article = None
    if cluster.representative_article_id is not None:
        for article in articles:
            if article.id == cluster.representative_article_id:
                representative_article = article
                break

    source_role_map: dict[str, str] = {}
    for article in articles:
        source_type = source_type_map.get(str(article.source_id), "other")
        source_role = classify_source_role(
            article_published_at=article.published_at,
            cluster_first_published_at=cluster.first_published_at,
            source_type=source_type,
            representative_title=(representative_article.title if representative_article else None),
            article_title=article.title,
        )
        source_role_map[str(article.id)] = source_role

    article_count = len(articles)
    unique_source_ids = {article.source_id for article in articles}
    source_count = len(unique_source_ids)

    provenance_complete = article_count > 0
    quality_flags: list[str] = []
    if article_count == 0:
        quality_flags.append("missing_evidence")
    if source_count <= 1:
        quality_flags.append("single_source")
    if source_count < 2:
        quality_flags.append("low_source_diversity")
    try:
        recent_conflicts = await container.conflict_repository.list_recent(limit=200)
        article_ids = {a.id for a in articles}
        conflict_count = sum(
            1 for c in recent_conflicts
            if c.article_a_id in article_ids or c.article_b_id in article_ids
        )
        if conflict_count > 0:
            quality_flags.append("conflicting_evidence")
        if conflict_count > 2:
            quality_flags.append("high_conflict")
    except Exception:
        conflict_count = 0

    overall_quality_score = max(
        0.0,
        min(
            1.0,
            (article_count / 5.0) * 0.3
            + (source_count / 5.0) * 0.3
            + max(0.0, 1.0 - (conflict_count / 3.0)) * 0.2
            + 0.1,
        ),
    )
    quality_explanation = f"{article_count} article(s); {source_count} independent source(s)"
    if conflict_count > 0:
        quality_explanation += f"; {conflict_count} conflict(s)"

    recent_articles = [
        {
            "id": str(article.id),
            "title": article.title,
            "url": article.url,
            "summary": article.summary,
            "published_at": article.published_at.isoformat(),
            "importance_score": article.importance_score,
            "confidence": article.confidence,
            "source_name": source_map.get(str(article.source_id)),
            "source_type": source_type_map.get(str(article.source_id)),
            "source_role": source_role_map.get(str(article.id)),
        }
        for article in articles[:20]
    ]

    timeline = build_timeline(articles, source_map)
    for item in timeline:
        item["source_role"] = source_role_map.get(item["id"])

    typed_timeline: list[TimelineItem] = cast(list[TimelineItem], timeline)

    what_changed = compute_what_changed(timeline)
    _ = [
        item.to_dict()
        for item in compute_what_changed_with_evidence(
            typed_timeline,
            detected_at=datetime.now(UTC).isoformat(),
        )
    ]

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
        contradictions = []
        needs_verification = False

    public_conflicts: list[PublicConflictResponse] = []
    try:
        conflict_repo = container.conflict_repository
        article_conflict_ids = {a.id for a in articles}
        recent_conflicts = await conflict_repo.list_recent(limit=200)
        for conflict in recent_conflicts:
            if (
                conflict.article_a_id in article_conflict_ids
                or conflict.article_b_id in article_conflict_ids
            ):
                source_a_name = source_map.get(str(conflict.source_a_id))
                source_b_name = source_map.get(str(conflict.source_b_id))
                pub_a = None
                pub_b = None
                for article in articles:
                    if article.id == conflict.article_a_id:
                        pub_a = article.published_at.isoformat()
                    if article.id == conflict.article_b_id:
                        pub_b = article.published_at.isoformat()
                public_conflicts.append(
                    PublicConflictResponse(
                        conflict_type=conflict.conflict_type.value,
                        status=conflict.status.value,
                        confidence=conflict.confidence,
                        explanation=conflict.explanation,
                        source_a_name=source_a_name,
                        source_b_name=source_b_name,
                        same_source=conflict.same_source,
                        published_at_a=pub_a,
                        published_at_b=pub_b,
                    )
                )
    except Exception:
        public_conflicts = []

    try:
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
        intelligence_confidence = (
            cluster_confidence.value
            if isinstance(cluster_confidence, Confidence)
            else cluster_confidence
        )
    except Exception:
        intelligence_confidence = "low"

    activity_status = None
    activity_score = None
    latest_activity_at = None
    related_companies: list[str] = []
    related_topics: list[str] = []
    relationship_count = 0
    graph_connections: list[dict[str, Any]] = []
    try:
        activity = await container.story_activity_repository.get_by_story_cluster_id(cluster.id)
        if activity is not None:
            activity_status = activity.status.value
            activity_score = activity.activity_score
            latest_activity_at = activity.evaluated_at.isoformat()
    except Exception:
        activity_status = None

    if get_settings().knowledge_graph_enabled:
        try:
            from ai_news_digest.application.services.graph_intelligence.graph_intelligence_service import (  # noqa: E501
                GraphIntelligenceService,
            )

            relationships = await container.relationship_repository.list_for_entity(
                entity_type="story",
                entity_id=cluster.id,
                status=None,
                limit=200,
            )
            relationship_count = len(relationships)
            company_ids = [
                str(r.object_entity_id)
                for r in relationships
                if r.object_entity_type.value == "company"
            ]
            topic_ids = [
                str(r.object_entity_id)
                for r in relationships
                if r.object_entity_type.value == "topic"
            ]
            if company_ids:
                companies = await container.company_repository.list_by_ids(company_ids)
                related_companies = [c.name for c in companies]
            if topic_ids:
                topics = await container.topic_repository.list_by_ids(topic_ids)
                related_topics = [t.name for t in topics]

            service = GraphIntelligenceService()
            name_map = await build_graph_name_map(container, relationships)
            name_map[f"story:{cluster.id}"] = cluster.title

            connections = service.get_entity_connections(
                entity_type="story",
                entity_id=str(cluster.id),
                relationships=relationships,
                name_resolver=lambda e_type, e_id: name_map.get(
                    f"{e_type}:{e_id}", f"{e_type} {e_id[:8]}"
                ),
            )
            graph_connections = [
                {
                    "entity_type": c.entity_type,
                    "entity_id": c.entity_id,
                    "name": c.name,
                    "relationship_type": c.relationship_type,
                    "status": c.status,
                    "score": round(c.score, 4),
                    "signals": c.signals,
                    "explanation": c.explanation,
                    "source_count": c.source_count,
                    "is_disputed": c.is_disputed,
                    "is_retracted": c.is_retracted,
                }
                for c in connections[:20]
            ]
        except Exception:
            graph_connections = []

    return PublicStoryClusterResponse(
        id=str(cluster.id),
        title=cluster.title,
        slug=cluster.slug,
        summary=cluster.summary,
        first_published_at=cluster.first_published_at.isoformat(),
        last_updated_at=cluster.last_updated_at.isoformat(),
        importance_score=cluster.importance_score,
        confidence=cluster.confidence,
        status=cluster.status.value,
        article_count=article_count,
        source_count=source_count,
        independent_source_count=source_count,
        recent_articles=recent_articles,
        timeline=timeline,
        what_changed=what_changed,
        contradictions=contradictions,
        conflicts=public_conflicts,
        needs_verification=needs_verification,
        intelligence_confidence=intelligence_confidence,
        activity_status=activity_status,
        activity_score=activity_score,
        latest_activity_at=latest_activity_at,
        related_companies=related_companies,
        related_topics=related_topics,
        relationship_count=relationship_count,
        graph_connections=graph_connections,
        provenance_complete=provenance_complete,
        quality_flags=quality_flags,
        quality_explanation=quality_explanation,
        overall_quality_score=overall_quality_score,
    )


@router.get(
    "/categories",
    response_model=list[PublicCategoryResponse],
    summary="List public categories",
)
async def list_public_categories(
    container: Annotated[Container, Depends(get_container)],
) -> list[PublicCategoryResponse]:
    """List all categories."""
    categories = await container.category_repository.list_all()

    return [
        PublicCategoryResponse(
            id=str(category.id),
            name=category.name,
            description=category.description,
        )
        for category in categories
    ]


@router.get(
    "/sources",
    response_model=list[SourceResponse],
    summary="List public sources",
)
async def list_public_sources(
    container: Annotated[Container, Depends(get_container)],
) -> list[SourceResponse]:
    """List all active news sources for the public experience."""
    sources = await container.source_repository.list_all()

    return [
        SourceResponse(
            id=source.id,
            name=source.name,
            feed_url=source.feed_url,
            website_url=source.website_url,
            description=source.description,
            is_active=source.is_active,
            status=source.status.value,
        )
        for source in sources
    ]


@router.get(
    "/story-clusters",
    response_model=PaginatedResponse[PublicStoryClusterSearchResponse],
    summary="List public story clusters with optional search",
)
async def list_public_story_clusters(
    container: Annotated[Container, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
    search: Annotated[str | None, Query(max_length=200)] = None,
    category_id: Annotated[str | None, Query()] = None,
    company_id: Annotated[str | None, Query()] = None,
    topic_id: Annotated[str | None, Query()] = None,
    published_from: Annotated[str | None, Query()] = None,
    published_to: Annotated[str | None, Query()] = None,
    min_importance: Annotated[float | None, Query(ge=0)] = None,
) -> PaginatedResponse[PublicStoryClusterSearchResponse]:
    """List publicly visible story clusters with optional filtering and search."""
    cat_id = UUID(category_id) if category_id else None
    comp_id = UUID(company_id) if company_id else None
    topic_uuid = UUID(topic_id) if topic_id else None

    published_from_dt: datetime | None = None
    published_to_dt: datetime | None = None
    if published_from:
        with contextlib.suppress(ValueError):
            published_from_dt = datetime.fromisoformat(published_from)
    if published_to:
        with contextlib.suppress(ValueError):
            published_to_dt = datetime.fromisoformat(published_to)

    clusters = await container.story_cluster_repository.search_public(
        search=search,
        category_id=cat_id,
        company_id=comp_id,
        topic_id=topic_uuid,
        published_from=published_from_dt,
        published_to=published_to_dt,
        min_importance=min_importance,
        limit=limit,
        offset=offset,
    )
    total = await container.story_cluster_repository.count_public(
        search=search,
        category_id=cat_id,
        company_id=comp_id,
        topic_id=topic_uuid,
        published_from=published_from_dt,
        published_to=published_to_dt,
        min_importance=min_importance,
    )

    activity_map = await _enrich_cluster_activity(container, [c.id for c in clusters])

    return PaginatedResponse(
        items=[
            PublicStoryClusterSearchResponse(
                id=str(cluster.id),
                title=cluster.title,
                slug=cluster.slug,
                summary=cluster.summary,
                first_published_at=cluster.first_published_at.isoformat(),
                importance_score=cluster.importance_score,
                confidence=cluster.confidence,
                status=cluster.status.value,
                article_count=getattr(cluster, "article_count", 0),
                source_count=getattr(cluster, "source_count", 0),
                **activity_map.get(str(cluster.id), {}),
            )
            for cluster in clusters
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


async def _enrich_cluster_activity(
    container: Container,
    cluster_ids: list[Any],
) -> dict[str, dict[str, Any]]:
    """Return activity metadata keyed by cluster ID for public responses."""
    activity_map: dict[str, dict[str, Any]] = {}
    for cid in cluster_ids:
        try:
            activity = await container.story_activity_repository.get_by_story_cluster_id(cid)
            if activity is not None:
                activity_map[str(cid)] = {
                    "activity_status": activity.status.value,
                    "activity_score": activity.activity_score,
                    "latest_activity_at": activity.evaluated_at.isoformat(),
                }
        except Exception:  # noqa: S110
            pass
    return activity_map


@router.get(
    "/companies",
    response_model=list[PublicCompanyResponse],
    summary="List public companies",
)
async def list_public_companies(
    container: Annotated[Container, Depends(get_container)],
) -> list[PublicCompanyResponse]:
    """List all known companies with article counts."""
    companies = await container.company_repository.list_all_with_counts()
    return [
        PublicCompanyResponse(
            id=str(company.id),
            name=company.name,
            description=None,
            article_count=getattr(company, "article_count", 0),
        )
        for company in companies
    ]


@router.get(
    "/topics",
    response_model=list[PublicTopicResponse],
    summary="List public topics",
)
async def list_public_topics(
    container: Annotated[Container, Depends(get_container)],
) -> list[PublicTopicResponse]:
    """List all known topics with article counts."""
    topics = await container.topic_repository.list_all_with_counts()
    return [
        PublicTopicResponse(
            id=str(topic.id),
            name=topic.name,
            description=None,
            article_count=getattr(topic, "article_count", 0),
        )
        for topic in topics
    ]


@router.get(
    "/trends",
    response_model=PaginatedResponse[PublicTrendSearchResponse],
    summary="List public trends",
)
async def list_public_trends(
    container: Annotated[Container, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
    trend_type: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    min_score: Annotated[float | None, Query(ge=0)] = None,
) -> PaginatedResponse[PublicTrendSearchResponse]:
    """List publicly visible trends with optional filtering."""
    trends = await container.trend_repository.list_public(
        trend_type=trend_type,
        status=status,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )
    total = await container.trend_repository.count_public(
        trend_type=trend_type,
        status=status,
        min_score=min_score,
    )
    return PaginatedResponse(
        items=[
            PublicTrendSearchResponse(
                id=str(trend.id),
                trend_type=trend.trend_type.value,
                display_name=trend.display_name,
                status=trend.status.value,
                trend_score=trend.trend_score,
                momentum_score=trend.momentum_score,
                recent_activity=trend.recent_activity,
                baseline_activity=trend.baseline_activity,
                source_count=trend.source_count,
                story_count=trend.story_count,
                event_count=trend.event_count,
                explanation=trend.explanation,
                first_detected_at=trend.first_detected_at.isoformat(),
                last_detected_at=trend.last_detected_at.isoformat(),
            )
            for trend in trends
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/trends/{trend_id}",
    response_model=PublicTrendResponse,
    summary="Get a public trend",
)
async def get_public_trend(
    trend_id: UUID,
    container: Annotated[Container, Depends(get_container)],
) -> PublicTrendResponse:
    """Retrieve a single public trend by ID."""
    trend = await container.trend_repository.get_by_id(trend_id)
    if trend is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Trend {trend_id} not found.")
    return PublicTrendResponse(
        id=str(trend.id),
        trend_type=trend.trend_type.value,
        display_name=trend.display_name,
        status=trend.status.value,
        trend_score=trend.trend_score,
        momentum_score=trend.momentum_score,
        recent_activity=trend.recent_activity,
        baseline_activity=trend.baseline_activity,
        source_count=trend.source_count,
        story_count=trend.story_count,
        event_count=trend.event_count,
        explanation=trend.explanation,
        first_detected_at=trend.first_detected_at.isoformat(),
        last_detected_at=trend.last_detected_at.isoformat(),
        trend_metadata=trend.trend_metadata if trend.trend_metadata else None,
        provenance_complete=trend.source_count > 0,
        quality_flags=[] if trend.source_count > 1 else ["single_source"],
    )


router.include_router(timeline_router)


__all__ = ["router"]
