from __future__ import annotations

from typing import Any

from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.ports.article_repository import ArticleRepository

logger = get_logger(__name__)


class ExtractArticleUseCase:
    """Extract full article content from a URL and persist it.

    The extraction pipeline fetches the article HTML, extracts the main
    text, cleans the content, and updates the article record. Failures
    are logged but never crash the pipeline.
    """

    def __init__(
        self,
        article_fetcher: Any,
        html_extractor: Any,
        content_cleaner: Any,
        article_repository: ArticleRepository,
    ) -> None:
        self._article_fetcher = article_fetcher
        self._html_extractor = html_extractor
        self._content_cleaner = content_cleaner
        self._article_repository = article_repository

    async def execute(self, article: Article) -> Article:
        """Extract article content and update the article record."""
        try:
            fetch_result = await self._article_fetcher.fetch(article.url)
        except Exception as exc:
            logger.warning(
                "Article extraction fetch failed",
                article_id=str(article.id),
                url=article.url,
                error=str(exc),
            )
            return article

        if not fetch_result or not fetch_result.content:
            logger.warning(
                "Article extraction returned empty content",
                article_id=str(article.id),
                url=article.url,
            )
            return article

        try:
            extracted_text = await self._html_extractor.extract(
                fetch_result.content,
                url=article.url,
            )
        except Exception as exc:
            logger.warning(
                "Article extraction failed",
                article_id=str(article.id),
                url=article.url,
                error=str(exc),
            )
            return article

        if not extracted_text:
            logger.warning(
                "HTML extractor returned empty text",
                article_id=str(article.id),
                url=article.url,
            )
            return article

        try:
            cleaned = self._content_cleaner.clean(extracted_text)
        except Exception as exc:
            logger.warning(
                "Content cleaning failed",
                article_id=str(article.id),
                error=str(exc),
            )
            cleaned = extracted_text

        article.content = cleaned
        article.content_char_count = len(cleaned)
        article.extraction_method = fetch_result.method
        article.extraction_quality = fetch_result.quality
        article.extracted_at = fetch_result.extracted_at

        return await self._article_repository.update(article)


__all__ = ["ExtractArticleUseCase"]
