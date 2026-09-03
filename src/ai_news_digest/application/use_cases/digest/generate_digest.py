from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from ai_news_digest.application.dto.digest_article_view import DigestArticleView
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.exceptions import ValidationError
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.category_repository import CategoryRepository
from ai_news_digest.domain.ports.digest_repository import DigestRepository
from ai_news_digest.domain.ports.source_repository import SourceRepository


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
        source_repository: SourceRepository,
        category_repository: CategoryRepository,
    ) -> None:
        self._article_repository = article_repository
        self._digest_repository = digest_repository
        self._source_repository = source_repository
        self._category_repository = category_repository

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

        return DigestGenerationResult(
            digest_id=persisted_digest.id,
            included_articles=len(selected_ids),
            generated_at=persisted_digest.generated_at,
        )

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
