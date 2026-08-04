from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.models.article import Article
from ai_news_digest.infrastructure.database.models.article_model import (
    ArticleModel,
)


class ArticleMapper:
    """
    Maps between Article domain objects and ArticleModel ORM entities.
    """

    @staticmethod
    def to_model(article: Article) -> ArticleModel:
        """
        Convert a domain Article into a new ORM ArticleModel.
        """
        return ArticleModel(
            id=str(article.id),
            source_id=str(article.source_id),
            category_id=(str(article.category_id) if article.category_id is not None else None),
            title=article.title,
            url=article.url,
            summary=article.summary,
            content=article.content,
            status=article.status,
            published_at=article.published_at,
            fetched_at=article.fetched_at,
        )

    @staticmethod
    def update_model(
        model: ArticleModel,
        article: Article,
    ) -> None:
        """
        Update an existing ORM model from a domain Article.
        """

        model.source_id = str(article.source_id)
        model.category_id = str(article.category_id) if article.category_id is not None else None
        model.title = article.title
        model.url = article.url
        model.summary = article.summary
        model.content = article.content
        model.status = article.status
        model.published_at = article.published_at
        model.fetched_at = article.fetched_at

    @staticmethod
    def to_domain(model: ArticleModel) -> Article:
        """
        Convert an ORM ArticleModel into a domain Article.
        """
        return Article(
            id=UUID(model.id),
            source_id=UUID(model.source_id),
            category_id=(UUID(model.category_id) if model.category_id is not None else None),
            title=model.title,
            url=model.url,
            summary=model.summary,
            content=model.content,
            status=model.status,
            published_at=model.published_at,
            fetched_at=model.fetched_at,
        )
