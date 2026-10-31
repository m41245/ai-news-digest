"""Unit tests for the LLM provider factory."""

from __future__ import annotations

from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.infrastructure.llm.factory import LLMProviderFactory
from ai_news_digest.infrastructure.llm.gemini_client import GeminiProvider
from ai_news_digest.infrastructure.llm.groq_client import GroqProvider


def test_factory_creates_gemini_provider() -> None:
    provider = LLMProviderFactory.create_gemini_provider(
        ProviderConfig(
            provider_name="gemini",
            api_key="test-api-key",
            model="gemini-2.5-flash",
        )
    )

    assert isinstance(provider, GeminiProvider)
    assert provider.id == "gemini"


def test_factory_creates_groq_provider() -> None:
    provider = LLMProviderFactory.create_groq_provider(
        ProviderConfig(
            provider_name="groq",
            api_key="test-api-key",
            model="openai/gpt-oss-20b",
        )
    )

    assert isinstance(provider, GroqProvider)
    assert provider.id == "groq"
