from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.cluster_status import ClusterStatus


@dataclass(slots=True)
class StoryCluster:
    """
    Represents a story cluster grouping multiple articles describing the
    same underlying AI development.
    """

    id: UUID
    title: str
    slug: str
    summary: str | None = None
    first_published_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    representative_article_id: UUID | None = None
    latest_article_id: UUID | None = None
    importance_score: float | None = None
    confidence: float | None = None
    status: ClusterStatus = ClusterStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        title: str,
        slug: str,
        summary: str | None = None,
        first_published_at: datetime | None = None,
        last_updated_at: datetime | None = None,
        representative_article_id: UUID | None = None,
        latest_article_id: UUID | None = None,
        importance_score: float | None = None,
        confidence: float | None = None,
    ) -> StoryCluster:
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            title=title,
            slug=slug,
            summary=summary,
            first_published_at=first_published_at or now,
            last_updated_at=last_updated_at or now,
            representative_article_id=representative_article_id,
            latest_article_id=latest_article_id,
            importance_score=importance_score,
            confidence=confidence,
            status=ClusterStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

    def touch(self) -> None:
        """Update the last_updated_at and updated_at timestamps."""
        self.last_updated_at = datetime.now(UTC)
        self.updated_at = self.last_updated_at

    def set_representative(self, article_id: UUID) -> None:
        """Set the representative article for this cluster."""
        self.representative_article_id = article_id
        self.touch()

    def update_importance(self, importance_score: float | None, confidence: float | None) -> None:
        """Update the importance and confidence scores."""
        self.importance_score = importance_score
        self.confidence = confidence
        self.touch()

    def set_latest_article(self, article_id: UUID) -> None:
        """Set the latest article for this cluster."""
        self.latest_article_id = article_id
        self.touch()

    def archive(self) -> None:
        """Archive this cluster."""
        self.status = ClusterStatus.ARCHIVED
        self.touch()

    def merge_into(self, target_cluster_id: UUID) -> None:
        """Mark this cluster as merged into another."""
        self.status = ClusterStatus.MERGED
        self.touch()


__all__ = ["StoryCluster"]
