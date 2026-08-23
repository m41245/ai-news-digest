from __future__ import annotations

from ai_news_digest.application.use_cases.article.categorize_article import (
    CategorizeArticleUseCase,
)
from ai_news_digest.application.use_cases.article.summarize_article import (
    SummarizeArticleUseCase,
)
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.ports.article_repository import ArticleRepository


class ProcessArticleUseCase:
    """Orchestrate the full AI processing pipeline for a single article.

    The pipeline runs summarization followed by categorization and persists
    the result. Each stage is idempotent: an article that has already been
    summarized will not be summarized again, and an article that has already
    been categorized will not be categorized again.
    """

    def __init__(
        self,
        summarize_use_case: SummarizeArticleUseCase,
        categorize_use_case: CategorizeArticleUseCase,
        article_repository: ArticleRepository,
    ) -> None:
        self._summarize = summarize_use_case
        self._categorize = categorize_use_case
        self._article_repository = article_repository

    async def execute(
        self,
        article: Article,
    ) -> Article:
        """Run summarize then categorize, persisting the final state."""
        from ai_news_digest.domain.enums.article_status import ArticleStatus

        if article.status == ArticleStatus.NEW:
            article = await self._summarize.execute(article)

        if article.status == ArticleStatus.SUMMARIZED:
            article = await self._categorize.execute(article)

        return await self._article_repository.update(article)


__all__ = ["ProcessArticleUseCase"]
