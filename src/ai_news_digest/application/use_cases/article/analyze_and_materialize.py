from __future__ import annotations

from typing import Any
from uuid import UUID

from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.category import Category
from ai_news_digest.domain.models.company import Company
from ai_news_digest.domain.models.topic import Topic
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.category_repository import CategoryRepository
from ai_news_digest.domain.ports.company_repository import CompanyRepository
from ai_news_digest.domain.ports.topic_repository import TopicRepository


class AnalyzeAndMaterializeUseCase:
    """Analyze an article and materialize companies, topics, and categories.

    This use case orchestrates AI analysis and persists the resulting
    structured entities (companies, topics, categories) into the database.
    """

    def __init__(
        self,
        analyze_use_case: Any,
        article_repository: ArticleRepository,
        company_repository: CompanyRepository,
        topic_repository: TopicRepository,
        category_repository: CategoryRepository,
    ) -> None:
        self._analyze_use_case = analyze_use_case
        self._article_repository = article_repository
        self._company_repository = company_repository
        self._topic_repository = topic_repository
        self._category_repository = category_repository

    async def execute(self, article: Article) -> Article:
        """Analyze and materialize article metadata."""
        analyzed = await self._analyze_use_case.execute(article)

        company_ids = await self._materialize_companies(analyzed)
        topic_ids = await self._materialize_topics(analyzed)
        category_ids = await self._materialize_categories(analyzed)

        analyzed.company_ids = company_ids
        analyzed.topic_ids = topic_ids
        analyzed.category_ids = category_ids
        analyzed.mark_analyzed()

        return await self._article_repository.update(analyzed)

    async def _materialize_companies(self, article: Article) -> tuple[UUID, ...]:
        """Create or resolve companies and return their IDs."""
        if not article.companies:
            return ()

        company_ids: list[UUID] = []
        for name in article.companies:
            existing = await self._company_repository.get_by_slug(name)
            if existing is not None:
                company_ids.append(existing.id)
            else:
                company = Company.create(name=name)
                created = await self._company_repository.create(company)
                company_ids.append(created.id)

        await self._article_repository.replace_companies(article.id, company_ids)
        return tuple(company_ids)

    async def _materialize_topics(self, article: Article) -> tuple[UUID, ...]:
        """Create or resolve topics and return their IDs."""
        if not article.topics:
            return ()

        topic_ids: list[UUID] = []
        for name in article.topics:
            existing = await self._topic_repository.get_by_slug(name)
            if existing is not None:
                topic_ids.append(existing.id)
            else:
                topic = Topic.create(name=name)
                created = await self._topic_repository.create(topic)
                topic_ids.append(created.id)

        await self._article_repository.replace_topics(article.id, topic_ids)
        return tuple(topic_ids)

    async def _materialize_categories(self, article: Article) -> tuple[UUID, ...]:
        """Create or resolve categories and return their IDs."""
        if not article.categories:
            return ()

        category_ids: list[UUID] = []
        for name in article.categories:
            existing = await self._category_repository.get_by_name(name)
            if existing is not None:
                category_ids.append(existing.id)
            else:
                category = Category.create(name=name)
                created = await self._category_repository.create(category)
                category_ids.append(created.id)

        await self._article_repository.replace_categories(article.id, category_ids)
        return tuple(category_ids)


__all__ = ["AnalyzeAndMaterializeUseCase"]
