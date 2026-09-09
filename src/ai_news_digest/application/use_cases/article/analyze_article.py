from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from ai_news_digest.application.ai.capability_registry import CapabilityRegistry
from ai_news_digest.application.ai.models import AIRequest, AIResponseFormat
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.domain.models.article import Article

_SYSTEM_PROMPT = (
    "You are an AI news analyst. Analyze the following article and return a "
    "JSON object with these exact fields:\n"
    '{"importance_score": <0.0-1.0>, "confidence": <0.0-1.0>, '
    '"key_takeaways": [<list of short strings>], '
    '"why_it_matters": "<string>", '
    '"companies": [<list of company names>], '
    '"topics": [<list of topic names>]}\n'
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

    Extracts structured intelligence (importance, confidence, key takeaways,
    companies, topics) from article content using an AI provider that
    advertises the ``analysis`` capability.
    """

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        provider_id: str | None,
    ) -> None:
        self._provider_registry = provider_registry
        self._provider_id = provider_id

    async def execute(self, article: Article) -> Article:
        """Analyze an article and update it with structured intelligence."""
        if self._provider_id is None:
            raise ExternalServiceError("No AI provider currently supports the analysis capability.")

        provider = self._provider_registry.get(self._provider_id)
        content = article.content or article.summary or article.title

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

        article.importance_score = _clamp_float(data.get("importance_score"))
        article.confidence = _clamp_float(data.get("confidence"))
        article.key_takeaways = tuple(
            str(t).strip() for t in data.get("key_takeaways", []) if str(t).strip()
        )
        article.why_it_matters = str(data.get("why_it_matters") or "").strip() or None
        article.companies = tuple(
            str(c).strip() for c in data.get("companies", []) if str(c).strip()
        )
        article.topics = tuple(str(t).strip() for t in data.get("topics", []) if str(t).strip())
        article.ai_provider = provider.provider_name
        article.ai_model = provider.model_name
        article.ai_processed_at = _utcnow()

        return article


def _clamp_float(value: Any) -> float | None:
    """Clamp a value to 0.0-1.0 range, or return None."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, v))


def _utcnow() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(UTC)


__all__ = ["AnalyzeArticleUseCase", "get_provider_priority_provider_id"]
