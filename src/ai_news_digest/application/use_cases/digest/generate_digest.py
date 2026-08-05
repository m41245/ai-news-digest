from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.digest_repository import DigestRepository


@dataclass(slots=True)
class DigestGenerationResult:
    """Result returned after creating a digest."""

    digest_id: UUID
    included_articles: int
    generated_at: datetime


class GenerateDigestUseCase:
    """Create a digest from digest-eligible articles."""

    def __init__(
        self,
        article_repository: ArticleRepository,
        digest_repository: DigestRepository,
    ) -> None:
        self._article_repository = article_repository
        self._digest_repository = digest_repository

    async def execute(
        self,
        *,
        title: str,
        content: str,
        limit: int | None = None,
    ) -> DigestGenerationResult:
        """Create a digest from eligible articles and persist it."""
        eligible_articles = await self._article_repository.list_digest_eligible(
            limit=limit,
        )

        if not eligible_articles:
            raise ValueError("No digest-eligible articles were found.")

        ordered_articles = sorted(
            eligible_articles,
            key=lambda article: (
                article.published_at,
                article.id,
            ),
            reverse=True,
        )

        selected_articles = ordered_articles
        selected_ids = [article.id for article in selected_articles]

        digest = Digest.create(
            title=title,
            content=content,
            digest_format=DigestFormat.MARKDOWN,
            article_ids=selected_ids,
        )

        persisted_digest = await self._digest_repository.create(digest)

        return DigestGenerationResult(
            digest_id=persisted_digest.id,
            included_articles=len(selected_ids),
            generated_at=persisted_digest.generated_at,
        )
