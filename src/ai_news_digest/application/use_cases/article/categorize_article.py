from __future__ import annotations

from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.models import AIRequest, AIResponseFormat
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.category import Category
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.category_repository import CategoryRepository


class CategorizeArticleUseCase:
    """Categorize a single article using the platform provider selection flow.

    The provider response is validated against a controlled category
    vocabulary. Arbitrary model output is never persisted as a category.
    """

    def __init__(
        self,
        decision_engine: DecisionEngine,
        provider_registry: ProviderRegistry,
        article_repository: ArticleRepository,
        category_repository: CategoryRepository,
    ) -> None:
        self._decision_engine = decision_engine
        self._provider_registry = provider_registry
        self._article_repository = article_repository
        self._category_repository = category_repository

    async def execute(
        self,
        article: Article,
    ) -> Article:
        """Categorize an article and persist the resulting domain update."""
        from ai_news_digest.application.ai.category_vocabulary import (
            normalize_category,
        )

        provider_ids = self._decision_engine.resolve({"categorization"})

        if not provider_ids:
            raise ExternalServiceError(
                "No AI provider currently supports the categorization capability."
            )

        provider_id = min(provider_ids)
        provider = self._provider_registry.get(provider_id)

        request = AIRequest(
            system_prompt=(
                "You are a precise news topic classifier. Return only a single "
                "category label that best fits the article. Valid categories "
                "include: AI Research, AI Models, AI Products, AI Infrastructure, "
                "AI Safety, AI Business, AI Policy, Robotics, Developer Tools."
            ),
            user_prompt=(
                f"Title: {article.title}\n\n"
                f"Summary: {article.summary}\n\n"
                f"Content: {article.content or article.summary}"
            ),
            temperature=0.1,
            max_tokens=64,
            response_format=AIResponseFormat.TEXT,
        )

        response = await provider.generate(request)
        raw_category = (response.content or "").strip()

        category_name = normalize_category(raw_category).value

        category = await self._category_repository.get_by_name(category_name)

        if category is None:
            matched = normalize_category(raw_category)
            category = Category.create(
                name=matched.value,
                description=matched.display_name,
            )
            category = await self._category_repository.create(category)

        article.mark_categorized()
        article.category_id = category.id

        return await self._article_repository.update(article)
