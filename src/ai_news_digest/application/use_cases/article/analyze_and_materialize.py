from __future__ import annotations

from typing import Any
from uuid import UUID

from ai_news_digest.application.ai.category_vocabulary import ArticleCategory
from ai_news_digest.application.ai.company_normalizer import normalize_company
from ai_news_digest.application.ai.topic_normalizer import dedupe_topics
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.category import Category
from ai_news_digest.domain.models.company import Company
from ai_news_digest.domain.models.topic import Topic
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.category_repository import CategoryRepository
from ai_news_digest.domain.ports.claim_repository import ClaimRepository
from ai_news_digest.domain.ports.company_repository import CompanyRepository
from ai_news_digest.domain.ports.topic_repository import TopicRepository


class AnalyzeAndMaterializeUseCase:
    """Analyze an article and materialize companies, topics, categories, and claims.

    This use case orchestrates AI analysis and persists the resulting
    structured entities (companies, topics, categories, claims) into the database.
    """

    def __init__(
        self,
        analyze_use_case: Any,
        article_repository: ArticleRepository,
        company_repository: CompanyRepository,
        topic_repository: TopicRepository,
        category_repository: CategoryRepository,
        claim_repository: ClaimRepository | None = None,
    ) -> None:
        self._analyze_use_case = analyze_use_case
        self._article_repository = article_repository
        self._company_repository = company_repository
        self._topic_repository = topic_repository
        self._category_repository = category_repository
        self._claim_repository = claim_repository

    async def execute(self, article: Article, source_id: UUID | None = None) -> Article:
        """Analyze and materialize article metadata."""
        analyzed = await self._analyze_use_case.execute(article)

        company_ids = await self._materialize_companies(analyzed)
        topic_ids = await self._materialize_topics(analyzed)
        category_ids = await self._materialize_categories(analyzed)

        analyzed.company_ids = company_ids
        analyzed.topic_ids = topic_ids
        analyzed.category_ids = category_ids
        analyzed.mark_analyzed()

        result = await self._article_repository.update(analyzed)

        if self._claim_repository is not None and source_id is not None:
            try:
                from ai_news_digest.application.use_cases.article.extract_claims import (
                    ExtractClaimsUseCase,
                )
                from ai_news_digest.application.ai.provider_manager import ProviderManager

                provider_manager = None
                for attr in ("_provider_manager",):
                    pm = getattr(self._analyze_use_case, attr, None)
                    if pm is not None:
                        provider_manager = pm
                        break

                if provider_manager is not None:
                    extract_claims = ExtractClaimsUseCase(
                        provider_manager=provider_manager,
                        claim_repository=self._claim_repository,
                    )
                    await extract_claims.execute(result, source_id)
            except Exception:
                pass

        return result

    async def _materialize_companies(self, article: Article) -> tuple[UUID, ...]:
        """Create or resolve companies and return their IDs."""
        if not article.companies:
            return ()

        company_ids: list[UUID] = []
        for name in article.companies:
            canonical = normalize_company(name)
            if canonical is None:
                continue
            existing = await self._company_repository.get_by_slug(canonical)
            if existing is not None:
                company_ids.append(UUID(str(existing.id)))
            else:
                company = Company.create(name=canonical)
                created = await self._company_repository.create(company)
                company_ids.append(UUID(str(created.id)))

        if company_ids:
            await self._article_repository.replace_companies(article.id, company_ids)
        return tuple(company_ids)

    async def _materialize_topics(self, article: Article) -> tuple[UUID, ...]:
        """Create or resolve topics and return their IDs."""
        if not article.topics:
            return ()

        normalized_topics = dedupe_topics(article.topics)
        topic_ids: list[UUID] = []
        for name in normalized_topics:
            existing = await self._topic_repository.get_by_slug(name)
            if existing is not None:
                topic_ids.append(UUID(str(existing.id)))
            else:
                topic = Topic.create(name=name)
                created = await self._topic_repository.create(topic)
                topic_ids.append(UUID(str(created.id)))

        if topic_ids:
            await self._article_repository.replace_topics(article.id, topic_ids)
        return tuple(topic_ids)

    async def _materialize_categories(self, article: Article) -> tuple[UUID, ...]:
        """Create or resolve categories and return their IDs."""
        if not article.categories:
            return ()

        seen_categories: set[str] = set()
        category_ids: list[UUID] = []
        for raw in article.categories:
            try:
                category_enum = ArticleCategory(raw)
            except ValueError:
                continue
            if category_enum.value in seen_categories:
                continue
            seen_categories.add(category_enum.value)
            existing = await self._category_repository.get_by_name(category_enum.value)
            if existing is not None:
                category_ids.append(UUID(str(existing.id)))
            else:
                category = Category.create(
                    name=category_enum.value,
                    description=category_enum.display_name,
                )
                created = await self._category_repository.create(category)
                category_ids.append(UUID(str(created.id)))

        if category_ids:
            await self._article_repository.replace_categories(article.id, category_ids)
        return tuple(category_ids)


__all__ = ["AnalyzeAndMaterializeUseCase"]
