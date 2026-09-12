"""
Unit tests for company normalization.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.ai.company_normalizer import (
    _KNOWN_COMPANIES,
    is_known_company,
    normalize_company,
)


class TestNormalizeCompany:
    def test_known_company_preserved(self) -> None:
        assert normalize_company("OpenAI") == "OpenAI"

    def test_alias_mapped_to_canonical(self) -> None:
        assert normalize_company("openai") == "OpenAI"
        assert normalize_company("OpenAI, Inc.") == "OpenAI"
        assert normalize_company("OpenAI's") == "OpenAI"

    def test_case_insensitive(self) -> None:
        assert normalize_company("GOOGLE") == "Google"
        assert normalize_company("anthropic") == "Anthropic"

    def test_whitespace_stripped(self) -> None:
        assert normalize_company("  OpenAI  ") == "OpenAI"

    def test_unknown_company_preserved(self) -> None:
        assert normalize_company("Acme Corp") == "Acme Corp"

    def test_empty_returns_none(self) -> None:
        assert normalize_company("") is None
        assert normalize_company("   ") is None


class TestIsKnownCompany:
    def test_known_company(self) -> None:
        assert is_known_company("OpenAI") is True
        assert is_known_company("openai") is True

    def test_unknown_company(self) -> None:
        assert is_known_company("Acme Corp") is False

    def test_empty(self) -> None:
        assert is_known_company("") is False


class TestKnownCompaniesRegistry:
    def test_all_known_companies_have_names(self) -> None:
        for company in _KNOWN_COMPANIES:
            assert company.name
            assert isinstance(company.name, str)

    def test_all_known_companies_have_unique_names(self) -> None:
        names = [c.name for c in _KNOWN_COMPANIES]
        assert len(names) == len(set(names))


__all__ = ["TestNormalizeCompany", "TestIsKnownCompany", "TestKnownCompaniesRegistry"]
