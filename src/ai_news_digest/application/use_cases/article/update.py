from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from ai_news_digest.application.dto.article import ArticleResponse, UpdateArticleRequest
from ai_news_digest.application.exceptions.article import ArticleNotFoundError

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.article_repository import ArticleRepository


class UpdateArticleUseCase:
    """
    Application use case responsible for updating an existing article.
    """

    def __init__(
        self,
        repository: ArticleRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        request: UpdateArticleRequest,
    ) -> ArticleResponse:
        """
        Update an existing article and return the updated representation.
        """
        article = await self._repository.get_by_id(UUID(request.id))

        if article is None:
            raise ArticleNotFoundError(request.id)

        if request.title is not None:
            article.title = request.title

        if request.summary is not None:
            article.summary = request.summary

        if request.content is not None:
            article.content = request.content

        if request.category_id is not None:
            article.category_id = UUID(request.category_id)

        updated = await self._repository.update(article)

        return ArticleResponse(
            id=str(updated.id),
            title=updated.title,
            url=updated.url,
            summary=updated.summary,
            content=updated.content,
            source_id=str(updated.source_id),
            category_id=str(updated.category_id) if updated.category_id else None,
            published_at=updated.published_at.isoformat(),
            fetched_at=updated.fetched_at.isoformat(),
            status=updated.status.value,
        )
