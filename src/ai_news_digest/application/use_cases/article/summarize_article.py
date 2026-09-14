from __future__ import annotations

from ai_news_digest.application.ai.models import AIRequest, AIResponseFormat
from ai_news_digest.application.ai.provider_manager import ProviderManager
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
        provider_manager: ProviderManager,
        article_repository: ArticleRepository,
        max_content_length: int = 8000,
    ) -> None:
        self._provider_manager = provider_manager
        self._article_repository = article_repository
        self._max_content_length = max_content_length

    async def execute(
        self,
        article: Article,
    ) -> Article:
        """Summarize an article and persist the resulting domain update."""
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

        response = await self._provider_manager.generate(
            request, capability="summarization"
        )
        summary_text = (response.content or article.summary).strip()

        if not summary_text:
            summary_text = article.summary

        article.summary = summary_text
        article.mark_summarized()

        return await self._article_repository.update(article)
