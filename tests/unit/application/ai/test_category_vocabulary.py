"""
Unit tests for the controlled category vocabulary.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.ai.category_vocabulary import (
    ArticleCategory,
    get_allowed_category_values,
    normalize_category,
    validate_category,
)
from ai_news_digest.application.ai.errors import AIConfigurationError


class TestArticleCategory:
    def test_all_categories_have_display_names(self) -> None:
        """Every category has a human-readable display name."""
        for category in ArticleCategory:
            assert category.display_name
            assert isinstance(category.display_name, str)

    def test_values_are_slugs(self) -> None:
        """Category values are lowercase slugs suitable for DB storage."""
        for category in ArticleCategory:
            assert category.value == category.value.lower()
            assert " " not in category.value


class TestNormalizeCategory:
    def test_exact_match(self) -> None:
        assert normalize_category("ai_research") == ArticleCategory.AI_RESEARCH

    def test_case_insensitive(self) -> None:
        assert normalize_category("AI_RESEARCH") == ArticleCategory.AI_RESEARCH
        assert normalize_category("Ai_Models") == ArticleCategory.AI_MODELS

    def test_hyphen_and_space_tolerance(self) -> None:
        assert normalize_category("ai-research") == ArticleCategory.AI_RESEARCH
        assert normalize_category("developer tools") == ArticleCategory.DEVELOPER_TOOLS

    def test_alias_mapping(self) -> None:
        assert normalize_category("llm") == ArticleCategory.AI_MODELS
        assert normalize_category("alignment") == ArticleCategory.AI_SAFETY
        assert normalize_category("robots") == ArticleCategory.ROBOTICS
        assert normalize_category("general") == ArticleCategory.OTHER

    def test_unknown_falls_back_to_other(self) -> None:
        assert normalize_category("quantum_biology") == ArticleCategory.OTHER

    def test_empty_falls_back_to_other(self) -> None:
        assert normalize_category("") == ArticleCategory.OTHER

    def test_whitespace_falls_back_to_other(self) -> None:
        assert normalize_category("   ") == ArticleCategory.OTHER


class TestValidateCategory:
    def test_valid_response(self) -> None:
        assert validate_category("AI Safety") == ArticleCategory.AI_SAFETY

    def test_empty_raises(self) -> None:
        with pytest.raises(AIConfigurationError, match="empty category"):
            validate_category("")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(AIConfigurationError, match="empty category"):
            validate_category("   ")


class TestAllowedValues:
    def test_returns_all_values(self) -> None:
        values = get_allowed_category_values()
        assert "ai_research" in values
        assert "other" in values
        assert len(values) == len(ArticleCategory)
