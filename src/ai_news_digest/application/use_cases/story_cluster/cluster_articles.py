from __future__ import annotations

import re
import string
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_cluster import StoryCluster

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.article_repository import ArticleRepository
    from ai_news_digest.domain.ports.story_cluster_repository import (
        StoryClusterRepository,
    )


def _normalize_text(text: str) -> tuple[str, ...]:
    text = text.lower().strip()
    text = text.translate(str.maketrans("", "", string.punctuation))
    words = text.split()
    return tuple(sorted(set(words)))


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def _generate_slug(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:128]


def _canonical_domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def _path_segments_overlap(url1: str, url2: str) -> bool:
    path1 = urlparse(url1).path
    path2 = urlparse(url2).path
    segments1 = {s for s in path1.split("/") if s}
    segments2 = {s for s in path2.split("/") if s}
    if not segments1 or not segments2:
        return False
    return bool(segments1 & segments2)


class ClusterArticlesUseCase:
    """
    Application use case responsible for clustering articles using
    deterministic signals.
    """

    def __init__(
        self,
        article_repository: ArticleRepository,
        cluster_repository: StoryClusterRepository,
    ) -> None:
        self._article_repository = article_repository
        self._cluster_repository = cluster_repository

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
            return existing

        clusters = await self._cluster_repository.list_all()

        best_cluster = None
        best_score = 0.0

        for cluster in clusters:
            score = await self._compute_score(article, cluster)
            if score > best_score:
                best_score = score
                best_cluster = cluster

        if best_cluster is not None and best_score >= 0.85:
            await self._article_repository.set_cluster(article.id, best_cluster.id)
            await self._cluster_repository.attach_article(best_cluster.id, article.id)
            updated_cluster = await self._update_cluster_metadata(best_cluster, article)
            return updated_cluster

        title = article.title[:500]
        slug = _generate_slug(title)
        new_cluster = StoryCluster.create(
            title=title,
            slug=slug,
            representative_article_id=article.id,
            importance_score=article.importance_score,
            confidence=article.confidence,
            first_published_at=article.published_at,
            last_updated_at=datetime.now(UTC),
        )
        created_cluster = await self._cluster_repository.create(new_cluster)
        await self._article_repository.set_cluster(article.id, created_cluster.id)
        await self._cluster_repository.attach_article(created_cluster.id, article.id)
        return None

    async def _compute_score(
        self,
        article: Article,
        cluster: StoryCluster,
    ) -> float:
        score = 0.0

        article_words = frozenset(_normalize_text(article.title))
        cluster_words = frozenset(_normalize_text(cluster.title))
        jaccard = _jaccard(article_words, cluster_words)

        if jaccard >= 0.8:
            score += 0.5
        elif jaccard >= 0.6:
            score += 0.25

        article_companies = {c.lower().strip() for c in article.companies}
        article_topics = {t.lower().strip() for t in article.topics}
        article_categories = {c.lower().strip() for c in article.categories}

        cluster_companies: set[str] = set()
        cluster_topics: set[str] = set()
        cluster_categories: set[str] = set()
        representative_url = ""

        if cluster.representative_article_id is not None:
            representative = await self._article_repository.get_by_id(
                cluster.representative_article_id
            )
            if representative is not None:
                cluster_companies = {c.lower().strip() for c in representative.companies}
                cluster_topics = {t.lower().strip() for t in representative.topics}
                cluster_categories = {c.lower().strip() for c in representative.categories}
                representative_url = representative.url

        if cluster_companies & article_companies:
            score += 0.2

        if cluster_topics & article_topics:
            score += 0.15

        if cluster_categories & article_categories:
            score += 0.1

        time_diff = abs((article.published_at - cluster.first_published_at).total_seconds())
        if time_diff <= 24 * 60 * 60:
            score += 0.2
        elif time_diff <= 7 * 24 * 60 * 60:
            score += 0.1

        if (
            representative_url
            and _canonical_domain(article.url) == _canonical_domain(representative_url)
            and _path_segments_overlap(article.url, representative_url)
        ):
            score += 0.05

        return score

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
