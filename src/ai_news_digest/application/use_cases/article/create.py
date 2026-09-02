from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from ai_news_digest.application.dto.article import ArticleResponse, CreateArticleRequest
from ai_news_digest.application.exceptions.article import ArticleAlreadyExistsError
from ai_news_digest.domain.models.article import Article

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.article_repository import ArticleRepository


class CreateArticleUseCase:
    """
    Application use case responsible for creating a news article.
    """

    def __init__(
        self,
        repository: ArticleRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        request: CreateArticleRequest,
    ) -> ArticleResponse:
        """
        Create a new article.
        """

        existing = await self._repository.get_by_url(request.url)

        if existing is not None:
            raise ArticleAlreadyExistsError(request.url)

        article = Article.create(
            title=request.title,
            url=request.url,
            summary=request.summary,
            content=request.content,
            source_id=UUID(request.source_id),
            published_at=datetime.fromisoformat(request.published_at),
            category_id=UUID(request.category_id) if request.category_id else None,
        )

        created = await self._repository.create(article)

        return ArticleResponse(
            id=str(created.id),
            title=created.title,
            url=created.url,
            summary=created.summary,
            content=created.content,
            source_id=str(created.source_id),
            category_id=str(created.category_id) if created.category_id else None,
            published_at=created.published_at.isoformat(),
            fetched_at=created.fetched_at.isoformat(),
            status=created.status.value,
        )
