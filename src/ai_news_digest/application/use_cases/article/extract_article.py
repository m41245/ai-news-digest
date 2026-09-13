from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.extraction_method import ExtractionMethod
from ai_news_digest.domain.enums.extraction_quality import ExtractionQuality
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.ports.article_repository import ArticleRepository

logger = get_logger(__name__)


@dataclass(slots=True)
class ContentQualityValidator:
    """Validate extracted article content quality."""

    min_char_count: int = 200
    min_avg_paragraph_length: int = 30

    def validate(self, content: str) -> tuple[ExtractionQuality, list[str]]:
        """Return (quality, reasons) for the given content."""
        stripped = content.strip()

        if not stripped or len(stripped) < self.min_char_count:
            return ExtractionQuality.NONE, ["content_too_short"]

        if "\n\n" in stripped:
            paragraphs = [p.strip() for p in stripped.split("\n\n") if p.strip()]
        else:
            paragraphs = [p.strip() for p in stripped.split("\n") if p.strip()]

        if len(paragraphs) < 2:
            return ExtractionQuality.LOW, ["insufficient_paragraphs"]

        avg_length = sum(len(p) for p in paragraphs) / len(paragraphs)
        if avg_length < self.min_avg_paragraph_length:
            return ExtractionQuality.LOW, ["low_paragraph_density"]

        return ExtractionQuality.HIGH, []


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
        quality_validator: ContentQualityValidator | None = None,
    ) -> None:
        self._article_fetcher = article_fetcher
        self._html_extractor = html_extractor
        self._content_cleaner = content_cleaner
        self._article_repository = article_repository
        self._quality_validator = quality_validator

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

        if self._quality_validator is not None:
            quality, reasons = self._quality_validator.validate(cleaned)
            if quality in (ExtractionQuality.NONE, ExtractionQuality.LOW) and article.content:
                article.extraction_method = ExtractionMethod.HTML
                article.extraction_quality = quality
                article.extracted_at = fetch_result.extracted_at
                article.content_char_count = len(cleaned)
                logger.warning(
                    "Article quality too low, keeping RSS content",
                    article_id=str(article.id),
                    url=article.url,
                    quality=quality.value,
                    reasons=str(reasons),
                )
                return await self._article_repository.update(article)
        else:
            quality = None

        article.content = cleaned
        article.content_char_count = len(cleaned)
        article.extraction_method = fetch_result.method
        article.extraction_quality = quality or fetch_result.quality
        article.extracted_at = fetch_result.extracted_at

        return await self._article_repository.update(article)


__all__ = ["ContentQualityValidator", "ExtractArticleUseCase"]
