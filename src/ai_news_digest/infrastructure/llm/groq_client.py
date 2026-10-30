from __future__ import annotations

from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.infrastructure.llm.openai_client import OpenAIProvider


class GroqProvider(OpenAIProvider):
    """Groq API implementation reusing the OpenAI-compatible adapter."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.base_url:
            config.base_url = "https://api.groq.com/openai/v1"
        if not config.model:
            config.model = "openai/gpt-oss-20b"
        super().__init__(config)
        self._provider_name = "groq"
        self._provider_label = "Groq"
        self._model_name = config.model or "openai/gpt-oss-20b"

    @property
    def id(self) -> str:
        return "groq"

    @property
    def name(self) -> str:
        return "Groq"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def description(self) -> str:
        return "Groq API provider for text generation and summarization."

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name


__all__ = ["GroqProvider"]
