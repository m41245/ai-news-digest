from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from ai_news_digest.application.dto.article import ArticleResponse
from ai_news_digest.application.exceptions.article import ArticleNotFoundError

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.article_repository import ArticleRepository


class GetArticleUseCase:
    """
    Application use case responsible for retrieving a news article.
    """

    def __init__(
        self,
        repository: ArticleRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        article_id: UUID,
    ) -> ArticleResponse:
        """
        Retrieve an article by its identifier.
        """

        article = await self._repository.get_by_id(article_id)

        if article is None:
            raise ArticleNotFoundError(str(article_id))

        return ArticleResponse(
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
