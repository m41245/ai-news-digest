"""Cluster articles into story clusters using semantic duplicate detection.

This use case coordinates bounded candidate selection, similarity scoring,
and cluster assignment. It preserves the existing representative-article
selection policy while delegating similarity classification to
``SemanticDuplicateDetector``.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from ai_news_digest.application.services.semantic_candidate_finder import (
    SemanticCandidateFinder,
)
from ai_news_digest.application.services.semantic_duplicate_detector import (
    SemanticDuplicateDetector,
)
from ai_news_digest.core.exceptions import DatabaseError
from ai_news_digest.core.logging import get_logger
from ai_news_digest.core.metrics import record_cluster_assigned, record_cluster_created
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_cluster import StoryCluster

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.article_repository import ArticleRepository
    from ai_news_digest.domain.ports.story_cluster_repository import (
        StoryClusterRepository,
    )

logger = get_logger(__name__)


class ClusterArticlesUseCase:
    """
    Application use case responsible for clustering articles using
    deterministic semantic duplicate detection.
    """

    def __init__(
        self,
        article_repository: ArticleRepository,
        cluster_repository: StoryClusterRepository,
        detector: SemanticDuplicateDetector | None = None,
        candidate_finder: SemanticCandidateFinder | None = None,
    ) -> None:
        self._article_repository = article_repository
        self._cluster_repository = cluster_repository
        self._detector = detector or SemanticDuplicateDetector()
        self._candidate_finder = candidate_finder or SemanticCandidateFinder(
            article_repository=article_repository,
            cluster_repository=cluster_repository,
        )

    async def execute(
        self,
        article: Article,
    ) -> StoryCluster | None:
        """
        Cluster the given article. Returns the cluster the article was attached to,
        or None if a new cluster was created.
        """

        if article.cluster_id is not None:
            existing = await self._cluster_repository.get_by_id(article.cluster_id)
            if existing is not None:
                return existing

        candidate_clusters, candidate_articles = await self._candidate_finder.find_candidates(
            article
        )

        best_cluster = None
        best_result = None

        for cluster in candidate_clusters:
            result = await self._detector.compare_with_cluster(
                article, cluster, article_repository=self._article_repository
            )
            if result.should_cluster() and (
                best_result is None or result.score > best_result.score
            ):
                best_result = result
                best_cluster = cluster

        if best_cluster is None:
            for candidate_article in candidate_articles:
                if candidate_article.cluster_id is None:
                    continue
                existing_cluster = await self._cluster_repository.get_by_id(
                    candidate_article.cluster_id
                )
                if existing_cluster is None:
                    continue
                result = await self._detector.compare_with_cluster(
                    article, existing_cluster, article_repository=self._article_repository
                )
                if result.should_cluster() and (
                    best_result is None or result.score > best_result.score
                ):
                    best_result = result
                    best_cluster = existing_cluster

        if best_cluster is not None:
            await self._article_repository.set_cluster(article.id, best_cluster.id)
            await self._cluster_repository.attach_article(best_cluster.id, article.id)
            updated_cluster = await self._update_cluster_metadata(best_cluster, article)
            record_cluster_assigned()
            logger.info(
                "Article assigned to existing cluster",
                article_id=str(article.id),
                cluster_id=str(best_cluster.id),
                score=best_result.score if best_result else None,
                signals=best_result.signals if best_result else (),
            )
            return updated_cluster

        title = article.title[:500]

        base_slug = _generate_slug(title)
        slug = base_slug
        get_by_slug = getattr(self._cluster_repository, "get_by_slug", None)
        if callable(get_by_slug):
            existing = await _lookup_slug(get_by_slug, slug)
            if existing is not None:
                counter = 2
                while counter <= 10000:
                    suffix = f"-{counter}"
                    candidate_base = base_slug[: max(1, 128 - len(suffix))].rstrip("-")
                    candidate = f"{candidate_base}{suffix}"
                    existing = await _lookup_slug(get_by_slug, candidate)
                    if existing is None:
                        slug = candidate
                        break
                    counter += 1
                else:
                    slug = f"{base_slug[:120]}-{uuid4().hex[:8]}"[:128]

        created_cluster = None
        last_error = None
        for _attempt in range(5):
            candidate_slug = slug if _attempt == 0 else f"{base_slug[:120]}-{uuid4().hex[:8]}"[:128]
            new_cluster = StoryCluster.create(
                title=title,
                slug=candidate_slug,
                representative_article_id=article.id,
                importance_score=article.importance_score,
                confidence=article.confidence,
                first_published_at=article.published_at,
                last_updated_at=datetime.now(UTC),
            )
            try:
                created_cluster = await self._cluster_repository.create(new_cluster)
                slug = candidate_slug
                break
            except Exception as exc:
                last_error = exc
                if not _is_unique_violation(exc):
                    raise
                continue
        if created_cluster is None:
            if last_error is not None:
                raise last_error
            raise RuntimeError("Failed to create story cluster")
        await self._article_repository.set_cluster(article.id, created_cluster.id)
        await self._cluster_repository.attach_article(created_cluster.id, article.id)
        record_cluster_created()
        logger.info(
            "New story cluster created",
            article_id=str(article.id),
            cluster_id=str(created_cluster.id),
        )
        return None

    async def _update_cluster_metadata(
        self,
        cluster: StoryCluster,
        article: Article,
    ) -> StoryCluster:
        now = datetime.now(UTC)

        cluster_articles = await self._article_repository.list_by_cluster_id(cluster.id)

        first_published_at = min(
            cluster.first_published_at,
            article.published_at,
        )

        representative = article
        for existing in cluster_articles:
            if existing.id == article.id:
                continue
            if (
                representative.importance_score is None
                or (
                    existing.importance_score is not None
                    and existing.importance_score > representative.importance_score
                )
                or (
                    representative.importance_score == existing.importance_score
                    and existing.published_at < representative.published_at
                )
            ):
                representative = existing

        all_articles = [article] + [a for a in cluster_articles if a.id != article.id]

        importance_scores = [
            a.importance_score for a in all_articles if a.importance_score is not None
        ]
        importance_score = max(importance_scores) if importance_scores else None

        confidences = [a.confidence for a in all_articles if a.confidence is not None]
        confidence = sum(confidences) / len(confidences) if confidences else None

        cluster.first_published_at = first_published_at
        cluster.last_updated_at = now
        cluster.representative_article_id = representative.id
        cluster.latest_article_id = article.id
        cluster.importance_score = importance_score
        cluster.confidence = confidence

        return await self._cluster_repository.update(cluster)


async def _lookup_slug(get_by_slug: Any, slug: str) -> Any:
    result = get_by_slug(slug)
    if inspect.isawaitable(result):
        result = await result
    return result


def _is_unique_violation(exc: Exception) -> bool:
    if isinstance(exc, IntegrityError):
        return True
    if isinstance(exc, DatabaseError):
        text = str(exc).lower()
        return "unique" in text or "integrity" in text or "constraint" in text
    return False


def _generate_slug(title: str) -> str:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", title or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower())
    slug = slug.strip("-")
    if not slug:
        slug = "story"
    return slug[:128]


__all__ = ["ClusterArticlesUseCase"]
