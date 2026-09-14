"""
Unit tests for GrokProvider.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AuthenticationError as OpenAIAuthError
from openai import RateLimitError as OpenAIRateLimitError

from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.application.ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIRateLimitError,
    AITransientError,
)
from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponseFormat,
)
from ai_news_digest.infrastructure.llm.grok_client import GrokProvider


@pytest.fixture
def provider_config() -> ProviderConfig:
    """Create a ProviderConfig for testing."""
    return ProviderConfig(
        provider_name="grok",
        api_key="test-api-key",
        enabled=True,
        priority=4,
        model="grok-2-latest",
        timeout=30,
        max_retries=3,
    )


@pytest.fixture
def grok_provider(provider_config: ProviderConfig) -> GrokProvider:
    """Create a GrokProvider instance."""
    return GrokProvider(provider_config)


def test_grok_provider_initialization(provider_config: ProviderConfig) -> None:
    """Test GrokProvider initialization."""
    provider = GrokProvider(provider_config)

    assert provider.provider_name == "grok"
    assert provider.model_name == "grok-2-latest"
    assert provider.priority() == 4
    assert provider.supports_streaming is True
    assert provider.supports_json_mode is True
    assert provider.supports_vision is True


def test_grok_provider_initialization_without_api_key() -> None:
    """Test GrokProvider initialization without API key."""
    config = ProviderConfig(
        provider_name="grok",
        api_key=None,
        enabled=True,
        priority=4,
    )
    provider = GrokProvider(config)

    assert provider._client is None


@pytest.mark.asyncio
async def test_grok_provider_available(grok_provider: GrokProvider) -> None:
    """Test available method."""
    assert await grok_provider.available() is True


@pytest.mark.asyncio
async def test_grok_provider_not_available_without_client() -> None:
    """Test available method when client is not configured."""
    config = ProviderConfig(
        provider_name="grok",
        api_key=None,
        enabled=True,
        priority=4,
    )
    provider = GrokProvider(config)

    assert await provider.available() is False


@pytest.mark.asyncio
async def test_grok_provider_generate_success(grok_provider: GrokProvider) -> None:
    """Test successful AI generation."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Summary text"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5
    mock_response.usage.total_tokens = 15

    with patch.object(
        grok_provider._client.chat.completions,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_response

        result = await grok_provider.generate(request)

        assert result.provider == "grok"
        assert result.model == "grok-2-latest"
        assert result.content == "Summary text"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
        assert result.usage.total_tokens == 15
        assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_grok_provider_generate_with_json_mode(grok_provider: GrokProvider) -> None:
    """Test AI generation with JSON mode."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
        response_format=AIResponseFormat.JSON,
    )

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"summary": "text"}'
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5
    mock_response.usage.total_tokens = 15

    with patch.object(
        grok_provider._client.chat.completions,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_response

        await grok_provider.generate(request)

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_grok_provider_generate_without_client() -> None:
    """Test generate raises error when client is not configured."""
    config = ProviderConfig(
        provider_name="grok",
        api_key=None,
        enabled=True,
        priority=4,
    )
    provider = GrokProvider(config)

    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with pytest.raises(AIConfigurationError, match="Grok client not configured"):
        await provider.generate(request)


@pytest.mark.asyncio
async def test_grok_provider_generate_api_error(grok_provider: GrokProvider) -> None:
    """Test generate handles API errors by mapping them to the error model."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with patch.object(
        grok_provider._client.chat.completions,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.side_effect = Exception("API Error")

        with pytest.raises(AITransientError, match="Grok request failed"):
            await grok_provider.generate(request)


@pytest.mark.asyncio
async def test_grok_provider_generate_auth_error(grok_provider: GrokProvider) -> None:
    """Authentication errors are mapped and not retried."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with patch.object(
        grok_provider._client.chat.completions,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.side_effect = OpenAIAuthError(
            message="Invalid API key",
            response=MagicMock(),
            body=None,
        )

        with pytest.raises(AIAuthenticationError, match="Grok authentication failed"):
            await grok_provider.generate(request)


@pytest.mark.asyncio
async def test_grok_provider_generate_rate_limit_error(grok_provider: GrokProvider) -> None:
    """Rate limit errors are mapped and not retried."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with patch.object(
        grok_provider._client.chat.completions,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.side_effect = OpenAIRateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body=None,
        )

        with pytest.raises(AIRateLimitError, match="Grok rate limit exceeded"):
            await grok_provider.generate(request)


@pytest.mark.asyncio
async def test_grok_provider_health_check_success(grok_provider: GrokProvider) -> None:
    """Test successful health check."""
    with patch.object(
        grok_provider._client.chat.completions,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = MagicMock()

        result = await grok_provider.health_check()

        assert result is True


@pytest.mark.asyncio
async def test_grok_provider_health_check_failure(grok_provider: GrokProvider) -> None:
    """Test health check on failure."""
    with patch.object(
        grok_provider._client.chat.completions,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.side_effect = Exception("Connection error")

        result = await grok_provider.health_check()

        assert result is False


@pytest.mark.asyncio
async def test_grok_provider_health_check_without_client() -> None:
    """Test health check when client is not configured."""
    config = ProviderConfig(
        provider_name="grok",
        api_key=None,
        enabled=True,
        priority=4,
    )
    provider = GrokProvider(config)

    result = await provider.health_check()

    assert result is False


def test_grok_provider_max_context_tokens(grok_provider: GrokProvider) -> None:
    """Test max_context_tokens property."""
    assert grok_provider.max_context_tokens == 128000


def test_grok_provider_max_context_tokens_custom() -> None:
    """Test max_context_tokens with custom context window."""
    config = ProviderConfig(
        provider_name="grok",
        api_key="test-key",
        enabled=True,
        priority=4,
        context_window=64000,
    )
    provider = GrokProvider(config)

    assert provider.max_context_tokens == 64000


@pytest.mark.asyncio
async def test_grok_provider_shutdown_closes_client(grok_provider: GrokProvider) -> None:
    """Test that shutdown() awaits client.close() when client exists."""
    mock_close = AsyncMock()
    with patch.object(grok_provider._client, "close", mock_close):
        await grok_provider.shutdown()

    mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_grok_provider_shutdown_without_client() -> None:
    """Test that shutdown() is safe when client is None."""
    config = ProviderConfig(
        provider_name="grok",
        api_key=None,
        enabled=True,
        priority=4,
    )
    provider = GrokProvider(config)

    await provider.shutdown()


__all__ = [
    "test_grok_provider_available",
    "test_grok_provider_generate_api_error",
    "test_grok_provider_generate_auth_error",
    "test_grok_provider_generate_rate_limit_error",
    "test_grok_provider_generate_success",
    "test_grok_provider_generate_with_json_mode",
    "test_grok_provider_generate_without_client",
    "test_grok_provider_health_check_failure",
    "test_grok_provider_health_check_success",
    "test_grok_provider_health_check_without_client",
    "test_grok_provider_initialization",
    "test_grok_provider_initialization_without_api_key",
    "test_grok_provider_max_context_tokens",
    "test_grok_provider_max_context_tokens_custom",
    "test_grok_provider_not_available_without_client",
    "test_grok_provider_shutdown_closes_client",
    "test_grok_provider_shutdown_without_client",
]
