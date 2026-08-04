from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.article_status import ArticleStatus


@dataclass(slots=True)
class Article:
    """
    Represents a normalized news article within the domain layer.
    """

    id: UUID
    title: str
    url: str
    summary: str
    content: str | None

    source_id: UUID
    category_id: UUID | None

    published_at: datetime
    fetched_at: datetime

    status: ArticleStatus

    @classmethod
    def create(
        cls,
        *,
        title: str,
        url: str,
        summary: str,
        content: str | None,
        source_id: UUID,
        published_at: datetime,
        category_id: UUID | None = None,
    ) -> Article:
        """
        Factory method for creating a newly ingested article.
        """

        return cls(
            id=uuid4(),
            title=title,
            url=url,
            summary=summary,
            content=content,
            source_id=source_id,
            category_id=category_id,
            published_at=published_at,
            fetched_at=datetime.now(UTC),
            status=ArticleStatus.NEW,
        )
