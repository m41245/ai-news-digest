from __future__ import annotations

from typing import TYPE_CHECKING

from ai_news_digest.application.dto.article import ArticleResponse

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.article_repository import ArticleRepository


class ListArticlesUseCase:
    """
    Application use case responsible for retrieving news articles.
    """

    def __init__(
        self,
        repository: ArticleRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        limit: int = 100,
    ) -> list[ArticleResponse]:
        """
        Retrieve articles ordered by published_at descending.
        """

        articles = await self._repository.list_recent(limit=limit)

        return [
            ArticleResponse(
                id=str(article.id),
                title=article.title,
                url=article.url,
                summary=article.summary,
                content=article.content,
                source_id=str(article.source_id),
                category_id=str(article.category_id) if article.category_id else None,
                published_at=article.published_at.isoformat(),
                fetched_at=article.fetched_at.isoformat(),
                status=article.status.value,
            )
            for article in articles
        ]
