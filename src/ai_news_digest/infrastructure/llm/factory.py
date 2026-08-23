from __future__ import annotations

from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.infrastructure.llm.anthropic_client import AnthropicProvider
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


__all__ = ["LLMProviderFactory"]
