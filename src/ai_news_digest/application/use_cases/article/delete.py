from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from ai_news_digest.application.exceptions.article import ArticleNotFoundError

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.article_repository import ArticleRepository


class DeleteArticleUseCase:
    """
    Application use case responsible for deleting an existing news article.
    """

    def __init__(
        self,
        repository: ArticleRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        article_id: UUID,
    ) -> None:
        """
        Delete a news article.

        Raises:
            ArticleNotFoundError: If the article does not exist.
        """

        article = await self._repository.get_by_id(article_id)

        if article is None:
            raise ArticleNotFoundError(str(article_id))

        await self._repository.delete(article_id)
