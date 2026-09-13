"""Lightweight DTOs for semantic duplicate detection.

These dataclasses carry only the fields needed by
``SemanticDuplicateDetector``, avoiding the need to load full domain
objects or ORM relationships for every candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ai_news_digest.domain.enums.semantic_match_type import SemanticMatchType


@dataclass(slots=True)
class CandidateCluster:
    """
    Lightweight view of a story cluster used for candidate matching.
    """

    id: UUID
    title: str
    first_published_at: datetime
    representative_article_id: UUID | None
    normalized_title_tokens: tuple[str, ...] = ()
    company_ids: frozenset[UUID] = frozenset()
    topic_ids: frozenset[UUID] = frozenset()
    category_ids: frozenset[UUID] = frozenset()
    source_domain: str = ""


@dataclass(slots=True)
class CandidateArticle:
    """
    Lightweight view of an article used for candidate matching.
    """

    id: UUID
    title: str
    normalized_title_tokens: tuple[str, ...] = ()
    company_ids: frozenset[UUID] = frozenset()
    topic_ids: frozenset[UUID] = frozenset()
    category_ids: frozenset[UUID] = frozenset()
    source_domain: str = ""
    published_at: datetime | None = None
    cluster_id: UUID | None = None


@dataclass(slots=True)
class SemanticMatchResult:
    """
    Result of comparing a candidate article/cluster against a new article.

    Attributes:
        match_type: Classification of the relationship.
        score: Normalized similarity score in [0.0, 1.0].
        candidate_id: The cluster or article ID that was compared.
        candidate_title: Title of the cluster or candidate article.
        signals: Deterministic signals that contributed to the score.
    """

    match_type: SemanticMatchType
    score: float
    candidate_id: UUID
    candidate_title: str
    signals: tuple[str, ...] = ()

    def is_duplicate(self) -> bool:
        """Return True if this result indicates a duplicate relationship."""
        return self.match_type in (
            SemanticMatchType.EXACT_DUPLICATE,
            SemanticMatchType.SEMANTIC_DUPLICATE,
        )

    def should_cluster(self) -> bool:
        """Return True if the article should be grouped into the candidate cluster."""
        return self.match_type == SemanticMatchType.SEMANTIC_DUPLICATE


__all__ = [
    "CandidateArticle",
    "CandidateCluster",
    "SemanticMatchResult",
]
