from __future__ import annotations

from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.models import AIRequest, AIResponseFormat
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.ports.article_repository import ArticleRepository


def _truncate(text: str | None, max_length: int) -> str:
    """Truncate text to *max_length* characters without breaking words."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    truncated = text[: max_length - 1]
    last_space = truncated.rfind(" ")
    if last_space > max_length // 2:
        return truncated[:last_space] + "…"
    return truncated + "…"


class SummarizeArticleUseCase:
    """Summarize a single article using the platform provider selection flow."""

    def __init__(
        self,
        decision_engine: DecisionEngine,
        provider_registry: ProviderRegistry,
        article_repository: ArticleRepository,
        max_content_length: int = 8000,
    ) -> None:
        self._decision_engine = decision_engine
        self._provider_registry = provider_registry
        self._article_repository = article_repository
        self._max_content_length = max_content_length

    async def execute(
        self,
        article: Article,
    ) -> Article:
        """Summarize an article and persist the resulting domain update."""
        provider_ids = self._decision_engine.resolve({"summarization"})

        if not provider_ids:
            raise ExternalServiceError(
                "No AI provider currently supports the summarization capability."
            )

        provider_id = min(provider_ids)
        provider = self._provider_registry.get(provider_id)

        content = _truncate(article.content or article.summary, self._max_content_length)

        request = AIRequest(
            system_prompt=(
                "You are a concise news summarizer. Produce a brief, factual, "
                "high-quality summary in plain text."
            ),
            user_prompt=(
                f"Title: {article.title}\n\n"
                f"Existing summary: {article.summary}\n\n"
                f"Content: {content}"
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
        article.mark_summarized()

        return await self._article_repository.update(article)
