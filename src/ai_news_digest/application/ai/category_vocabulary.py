from __future__ import annotations

from enum import Enum

from ai_news_digest.application.ai.errors import AIConfigurationError


class ArticleCategory(str, Enum):
    """Controlled vocabulary for article categorization.

    The AI response is validated against these values. Arbitrary model output
    is never persisted directly.
    """

    AI_RESEARCH = "ai_research"
    AI_MODELS = "ai_models"
    AI_PRODUCTS = "ai_products"
    AI_INFRASTRUCTURE = "ai_infrastructure"
    AI_SAFETY = "ai_safety"
    AI_BUSINESS = "ai_business"
    AI_POLICY = "ai_policy"
    ROBOTICS = "robotics"
    DEVELOPER_TOOLS = "developer_tools"
    OTHER = "other"

    @property
    def display_name(self) -> str:
        """Human-readable label for the category."""
        return self.value.replace("_", " ").title()


def get_allowed_category_values() -> set[str]:
    """Return the raw string values of every allowed category."""
    return {category.value for category in ArticleCategory}


def normalize_category(raw: str) -> ArticleCategory:
    """Map a raw provider response to a valid category.

    Matching is case-insensitive and tolerant of minor whitespace/punctuation
    differences. Unrecognized input falls back to ``ArticleCategory.OTHER``
    rather than raising, so the pipeline never crashes on model output.
    """
    cleaned = raw.strip().lower().replace("-", "_").replace(" ", "_")

    for category in ArticleCategory:
        if cleaned == category.value:
            return category

    aliases = {
        "research": ArticleCategory.AI_RESEARCH,
        "ai research": ArticleCategory.AI_RESEARCH,
        "models": ArticleCategory.AI_MODELS,
        "llm": ArticleCategory.AI_MODELS,
        "products": ArticleCategory.AI_PRODUCTS,
        "product": ArticleCategory.AI_PRODUCTS,
        "infrastructure": ArticleCategory.AI_INFRASTRUCTURE,
        "safety": ArticleCategory.AI_SAFETY,
        "alignment": ArticleCategory.AI_SAFETY,
        "business": ArticleCategory.AI_BUSINESS,
        "industry": ArticleCategory.AI_BUSINESS,
        "policy": ArticleCategory.AI_POLICY,
        "regulation": ArticleCategory.AI_POLICY,
        "robotics": ArticleCategory.ROBOTICS,
        "robots": ArticleCategory.ROBOTICS,
        "developer": ArticleCategory.DEVELOPER_TOOLS,
        "tools": ArticleCategory.DEVELOPER_TOOLS,
        "general": ArticleCategory.OTHER,
        "misc": ArticleCategory.OTHER,
        "miscellaneous": ArticleCategory.OTHER,
    }

    normalized = aliases.get(cleaned)
    if normalized is not None:
        return normalized

    return ArticleCategory.OTHER


def validate_category(raw: str) -> ArticleCategory:
    """Validate and return a category for a raw provider response.

    Raises ``AIConfigurationError`` only when *raw* is empty/whitespace, which
    indicates the provider returned no usable content at all.
    """
    if not raw or not raw.strip():
        raise AIConfigurationError("Provider returned an empty category response.")
    return normalize_category(raw)


__all__ = [
    "ArticleCategory",
    "get_allowed_category_values",
    "normalize_category",
    "validate_category",
]
