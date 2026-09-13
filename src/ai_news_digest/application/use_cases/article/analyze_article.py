from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from ai_news_digest.application.ai.capability_registry import CapabilityRegistry
from ai_news_digest.application.ai.category_vocabulary import (
    get_allowed_category_values,
    normalize_category,
)
from ai_news_digest.application.ai.company_normalizer import normalize_company
from ai_news_digest.application.ai.models import AIRequest, AIResponseFormat
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.application.ai.structured_output import (
    validate_structured_output,
)
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.domain.models.article import Article

_ANALYSIS_PROMPT_VERSION = "v1"

_SYSTEM_PROMPT = (
    "You are an AI news analyst. Analyze the following article and return a "
    "JSON object with these exact fields:\n"
    '{"summary": "<concise factual summary>", '
    '"key_takeaways": ["<short string>", "..."], '
    '"why_it_matters": "<string>", '
    '"categories": ["<category slug>", "..."], '
    '"companies": ["<company name>", "..."], '
    '"topics": ["<topic name>", "..."], '
    '"confidence": <0.0-1.0>, '
    '"importance": <0.0-1.0>}\n'
    "Rules:\n"
    "- summary: 1-3 sentences, factual, concise.\n"
    "- key_takeaways: 1-6 short bullet-style strings.\n"
    "- why_it_matters: 1-2 sentences explaining significance.\n"
    "- categories: one or more of: "
    + ", ".join(sorted(get_allowed_category_values()))
    + ".\n"
    "- companies: named entities only. Do NOT include generic terms.\n"
    "- topics: short keyword phrases.\n"
    "- confidence: your confidence in the analysis, 0.0-1.0.\n"
    "- importance: how important this news is, 0.0-1.0.\n"
    "Return ONLY valid JSON. No markdown, no commentary."
)


def get_provider_priority_provider_id(
    provider_registry: ProviderRegistry,
    capability_registry: CapabilityRegistry,
) -> str | None:
    """Return the highest-priority provider that supports analysis."""
    if not capability_registry.exists("analysis"):
        return None

    provider_ids = capability_registry.providers_for("analysis")

    if not provider_ids:
        return None

    providers = [
        provider_registry.get(pid) for pid in provider_ids if provider_registry.exists(pid)
    ]

    if not providers:
        return None

    providers.sort(key=lambda p: p.priority(), reverse=True)
    return providers[0].id


class AnalyzeArticleUseCase:
    """Analyze a single article using the platform provider selection flow.

    Extracts validated structured intelligence from article content using an
    AI provider that advertises the ``analysis`` capability.
    """

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        provider_id: str | None,
    ) -> None:
        self._provider_registry = provider_registry
        self._provider_id = provider_id
        self._prompt_version = _ANALYSIS_PROMPT_VERSION

    async def execute(self, article: Article) -> Article:
        """Analyze an article and update it with structured intelligence."""
        if self._provider_id is None:
            raise ExternalServiceError("No AI provider currently supports the analysis capability.")

        provider = self._provider_registry.get(self._provider_id)
        content = _safe_article_text(article)

        request = AIRequest(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=(
                f"Title: {article.title}\n\n"
                f"Summary: {article.summary}\n\n"
                f"Content: {content}"
            ),
            temperature=0.2,
            max_tokens=1024,
            response_format=AIResponseFormat.JSON,
            metadata={"prompt_version": self._prompt_version, "article_id": str(article.id)},
        )

        response = await provider.generate(request)
        raw_content = (response.content or "").strip()

        if not raw_content:
            raise ExternalServiceError("AI provider returned an empty analysis response.")

        try:
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_content)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            data = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ExternalServiceError(f"Invalid JSON response from AI provider: {exc}") from exc

        if not isinstance(data, dict):
            raise ExternalServiceError("AI provider returned a non-object JSON response.")

        try:
            intelligence = validate_structured_output(data)
        except ValueError as exc:
            raise ExternalServiceError(f"Invalid structured analysis: {exc}") from exc

        article.importance_score = intelligence.importance
        article.confidence = intelligence.confidence
        article.key_takeaways = intelligence.key_takeaways
        article.why_it_matters = intelligence.why_it_matters
        article.summary = intelligence.summary
        article.ai_provider = provider.provider_name
        article.ai_model = provider.model_name
        article.ai_processed_at = _utcnow()

        normalized_categories = tuple(
            normalize_category(c).value for c in intelligence.categories
        )
        article.categories = normalized_categories

        normalized_companies = tuple(
            name for c in intelligence.companies if (name := normalize_company(c)) is not None
        )
        article.companies = normalized_companies

        article.topics = intelligence.topics

        if response.usage:
            article.ai_input_tokens = response.usage.prompt_tokens
            article.ai_output_tokens = response.usage.completion_tokens

        return article


def _safe_article_text(article: Article) -> str:
    """Return bounded, safe text for AI consumption.

    Never sends unbounded raw HTML. Prefers cleaned content, falls back
    to the RSS summary, then title.
    """
    if article.content:
        text = article.content
    elif article.summary:
        text = article.summary
    else:
        text = article.title

    max_chars = 8000
    if len(text) > max_chars:
        text = text[: max_chars - 1] + "…"

    return text


def _utcnow() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(UTC)


__all__ = ["_ANALYSIS_PROMPT_VERSION", "AnalyzeArticleUseCase", "get_provider_priority_provider_id"]
