from __future__ import annotations

from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.infrastructure.llm.anthropic_client import AnthropicProvider
from ai_news_digest.infrastructure.llm.gemini_client import GeminiProvider
from ai_news_digest.infrastructure.llm.grok_client import GrokProvider
from ai_news_digest.infrastructure.llm.openai_client import OpenAIProvider


class LLMProviderFactory:
    """Factory for creating AI provider instances based on configuration."""

    @staticmethod
    def create_openai_provider(config: ProviderConfig) -> OpenAIProvider:
        """Create an OpenAI provider instance."""
        return OpenAIProvider(config)

    @staticmethod
    def create_anthropic_provider(config: ProviderConfig) -> AnthropicProvider:
        """Create an Anthropic provider instance."""
        return AnthropicProvider(config)

    @staticmethod
    def create_gemini_provider(config: ProviderConfig) -> GeminiProvider:
        """Create a Gemini provider instance."""
        return GeminiProvider(config)

    @staticmethod
    def create_grok_provider(config: ProviderConfig) -> GrokProvider:
        """Create a Grok provider instance."""
        return GrokProvider(config)


__all__ = ["LLMProviderFactory"]
