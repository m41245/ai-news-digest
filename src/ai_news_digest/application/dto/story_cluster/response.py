from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class StoryClusterResponse:
    """
    Response DTO representing a story cluster.
    """

    id: str
    title: str
    slug: str
    summary: str | None
    first_published_at: str
    last_updated_at: str
    representative_article_id: str | None
    importance_score: float | None
    confidence: float | None
    status: str
    latest_article_id: str | None = None
    article_count: int = 0
    source_count: int = 0


@dataclass(slots=True, frozen=True)
class StoryClusterArticleResponse:
    """
    Response DTO representing an article within a story cluster.
    """

    id: str
    title: str
    url: str
    summary: str
    published_at: str
    importance_score: float | None
    confidence: float | None
    source_name: str | None = None
    source_type: str | None = None
    source_role: str | None = None
    source_role_confidence: str | None = None
    confidence_label: str | None = None


@dataclass(slots=True, frozen=True)
class StoryClusterDetailResponse(StoryClusterResponse):
    """
    Response DTO representing a story cluster with its recent articles.
    """

    recent_articles: list[StoryClusterArticleResponse] = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)
    what_changed: list[str] = field(default_factory=list)
    what_changed_evidence: list[dict] = field(default_factory=list)
    contradictions: list[dict] = field(default_factory=list)
    needs_verification: bool = False
    intelligence_confidence: str = "low"
