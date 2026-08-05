from __future__ import annotations

from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.models import AIRequest, AIResponseFormat
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.ports.article_repository import ArticleRepository


class SummarizeArticleUseCase:
    """Summarize a single article using the platform provider selection flow."""

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
        """Summarize an article and persist the resulting domain update."""
        provider_ids = self._decision_engine.resolve({"summarization"})

        if not provider_ids:
            raise RuntimeError(
                "No AI provider currently supports the summarization capability."
            )

        provider_id = min(provider_ids)
        provider = self._provider_registry.get(provider_id)

        request = AIRequest(
            system_prompt=(
                "You are a concise news summarizer. Produce a brief, factual, "
                "high-quality summary in plain text."
            ),
            user_prompt=(
                f"Title: {article.title}\n\n"
                f"Existing summary: {article.summary}\n\n"
                f"Content: {article.content or article.summary}"
            ),
            temperature=0.2,
            max_tokens=512,
            response_format=AIResponseFormat.TEXT,
        )

        response = await provider.generate(request)
        summary_text = (response.content or article.summary).strip()

        if not summary_text:
            summary_text = article.summary

        article.summary = summary_text
        article.status = ArticleStatus.SUMMARIZED

        return await self._article_repository.update(article)
