"""Unit tests for the Groq provider adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AuthenticationError as OpenAIAuthError

from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.application.ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidResponseError,
)
from ai_news_digest.application.ai.models import AIRequest
from ai_news_digest.infrastructure.llm.groq_client import GroqProvider


def test_groq_provider_initialization() -> None:
    config = ProviderConfig(
        provider_name="groq",
        api_key="test-api-key",
        enabled=True,
        priority=2,
        model="openai/gpt-oss-20b",
    )

    provider = GroqProvider(config)

    assert provider.id == "groq"
    assert provider.provider_name == "groq"
    assert provider.model_name == "openai/gpt-oss-20b"
    assert provider.priority() == 2
    assert config.base_url == "https://api.groq.com/openai/v1"


@pytest.mark.asyncio
async def test_groq_provider_generate_without_client() -> None:
    config = ProviderConfig(
        provider_name="groq",
        api_key=None,
        enabled=True,
        priority=2,
    )
    provider = GroqProvider(config)
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with pytest.raises(AIConfigurationError, match="Groq client not configured"):
        await provider.generate(request)


@pytest.mark.asyncio
async def test_groq_provider_generate_auth_error() -> None:
    config = ProviderConfig(
        provider_name="groq",
        api_key="test-api-key",
        enabled=True,
        priority=2,
        model="openai/gpt-oss-20b",
    )
    provider = GroqProvider(config)
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with patch.object(
        provider._client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = OpenAIAuthError(
            message="Invalid API key",
            response=MagicMock(),
            body=None,
        )

        with pytest.raises(AIAuthenticationError, match="Groq authentication failed"):
            await provider.generate(request)


@pytest.mark.asyncio
async def test_groq_provider_generate_empty_choices() -> None:
    config = ProviderConfig(
        provider_name="groq",
        api_key="test-api-key",
        enabled=True,
        priority=2,
        model="openai/gpt-oss-20b",
    )
    provider = GroqProvider(config)
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    mock_response = MagicMock()
    mock_response.choices = []

    with patch.object(
        provider._client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        with pytest.raises(AIInvalidResponseError, match="Groq API returned an empty choices list"):
            await provider.generate(request)


@pytest.mark.asyncio
async def test_groq_provider_generate_malformed_response() -> None:
    config = ProviderConfig(
        provider_name="groq",
        api_key="test-api-key",
        enabled=True,
        priority=2,
        model="openai/gpt-oss-20b",
    )
    provider = GroqProvider(config)
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with patch.object(
        provider._client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = ValueError("bad payload")

        with pytest.raises(AIInvalidResponseError, match="Invalid Groq response"):
            await provider.generate(request)
