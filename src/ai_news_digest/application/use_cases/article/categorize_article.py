from __future__ import annotations

from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.models import AIRequest, AIResponseFormat
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.ports.article_repository import ArticleRepository


class CategorizeArticleUseCase:
    """Categorize a single article using the platform provider selection flow."""

    def __init__(
        self,
        decision_engine: DecisionEngine,
        provider_registry: ProviderRegistry,
        article_repository: ArticleRepository,
    ) -> None:
        self._decision_engine = decision_engine
        self._provider_registry = provider_registry
        self._article_repository = article_repository

    async def execute(
        self,
        article: Article,
    ) -> Article:
        """Categorize an article and persist the resulting domain update."""
        provider_ids = self._decision_engine.resolve({"categorization"})

        if not provider_ids:
            raise RuntimeError(
                "No AI provider currently supports the categorization capability."
            )

        provider_id = min(provider_ids)
        provider = self._provider_registry.get(provider_id)

        request = AIRequest(
            system_prompt=(
                "You are a precise news topic classifier. Return only a single "
                "category label that best fits the article."
            ),
            user_prompt=(
                f"Title: {article.title}\n\n"
                f"Summary: {article.summary}\n\n"
                f"Content: {article.content or article.summary}"
            ),
            temperature=0.1,
            max_tokens=128,
            response_format=AIResponseFormat.TEXT,
        )

        response = await provider.generate(request)
        normalized_category = response.content.strip()

        if not normalized_category:
            normalized_category = "general"

        article.status = ArticleStatus.CATEGORIZED

        if article.category_id is None:
            article.category_id = None

        return await self._article_repository.update(article)
