"""
Unit tests for OpenAIProvider.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponseFormat,
)
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.infrastructure.llm.openai_client import OpenAIProvider


@pytest.fixture
def provider_config() -> ProviderConfig:
    """Create a ProviderConfig for testing."""
    return ProviderConfig(
        provider_name="openai",
        api_key="test-api-key",
        enabled=True,
        priority=1,
        model="gpt-4o-mini",
        timeout=30,
        max_retries=3,
    )


@pytest.fixture
def openai_provider(provider_config: ProviderConfig) -> OpenAIProvider:
    """Create an OpenAIProvider instance."""
    return OpenAIProvider(provider_config)


def test_openai_provider_initialization(provider_config: ProviderConfig) -> None:
    """Test OpenAIProvider initialization."""
    provider = OpenAIProvider(provider_config)

    assert provider.provider_name == "openai"
    assert provider.model_name == "gpt-4o-mini"
    assert provider.priority() == 1
    assert provider.supports_streaming is True
    assert provider.supports_json_mode is True
    assert provider.supports_vision is True


def test_openai_provider_initialization_without_api_key() -> None:
    """Test OpenAIProvider initialization without API key."""
    config = ProviderConfig(
        provider_name="openai",
        api_key=None,
        enabled=True,
        priority=1,
    )
    provider = OpenAIProvider(config)

    assert provider._client is None


@pytest.mark.asyncio
async def test_openai_provider_available(openai_provider: OpenAIProvider) -> None:
    """Test available method."""
    assert await openai_provider.available() is True


@pytest.mark.asyncio
async def test_openai_provider_not_available_without_client() -> None:
    """Test available method when client is not configured."""
    config = ProviderConfig(
        provider_name="openai",
        api_key=None,
        enabled=True,
        priority=1,
    )
    provider = OpenAIProvider(config)

    assert await provider.available() is False


@pytest.mark.asyncio
async def test_openai_provider_generate_success(openai_provider: OpenAIProvider) -> None:
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
        openai_provider._client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        result = await openai_provider.generate(request)

        assert result.provider == "openai"
        assert result.model == "gpt-4o-mini"
        assert result.content == "Summary text"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
        assert result.usage.total_tokens == 15
        assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_openai_provider_generate_with_none_usage(openai_provider: OpenAIProvider) -> None:
    """Test generation when OpenAI response usage is None."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Summary text"
    mock_response.usage = None

    with patch.object(
        openai_provider._client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        result = await openai_provider.generate(request)

        assert result.provider == "openai"
        assert result.model == "gpt-4o-mini"
        assert result.content == "Summary text"
        assert result.usage.prompt_tokens == 0
        assert result.usage.completion_tokens == 0
        assert result.usage.total_tokens == 0
        assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_openai_provider_generate_with_json_mode(openai_provider: OpenAIProvider) -> None:
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
        openai_provider._client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        await openai_provider.generate(request)

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_openai_provider_generate_without_client() -> None:
    """Test generate raises error when client is not configured."""
    config = ProviderConfig(
        provider_name="openai",
        api_key=None,
        enabled=True,
        priority=1,
    )
    provider = OpenAIProvider(config)

    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with pytest.raises(ExternalServiceError, match="OpenAI client not configured"):
        await provider.generate(request)


@pytest.mark.asyncio
async def test_openai_provider_generate_api_error(openai_provider: OpenAIProvider) -> None:
    """Test generate handles API errors by mapping them to the error model."""
    from ai_news_digest.application.ai.errors import AITransientError

    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with patch.object(
        openai_provider._client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = Exception("API Error")

        with pytest.raises(AITransientError, match="OpenAI request failed"):
            await openai_provider.generate(request)


@pytest.mark.asyncio
async def test_openai_provider_generate_auth_error(
    openai_provider: OpenAIProvider,
) -> None:
    """Authentication errors are mapped and not retried."""
    from openai import AuthenticationError as OpenAIAuthError

    from ai_news_digest.application.ai.errors import AIAuthenticationError

    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with patch.object(
        openai_provider._client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = OpenAIAuthError(
            message="Invalid API key",
            response=MagicMock(),
            body=None,
        )

        with pytest.raises(AIAuthenticationError, match="authentication failed"):
            await openai_provider.generate(request)


@pytest.mark.asyncio
async def test_openai_provider_health_check_success(openai_provider: OpenAIProvider) -> None:
    """Test successful health check."""
    with patch.object(openai_provider._client.models, "list", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = []

        result = await openai_provider.health_check()

        assert result is True


@pytest.mark.asyncio
async def test_openai_provider_health_check_failure(openai_provider: OpenAIProvider) -> None:
    """Test health check on failure."""
    with patch.object(openai_provider._client.models, "list", new_callable=AsyncMock) as mock_list:
        mock_list.side_effect = Exception("Connection error")

        result = await openai_provider.health_check()

        assert result is False


@pytest.mark.asyncio
async def test_openai_provider_health_check_without_client() -> None:
    """Test health check when client is not configured."""
    config = ProviderConfig(
        provider_name="openai",
        api_key=None,
        enabled=True,
        priority=1,
    )
    provider = OpenAIProvider(config)

    result = await provider.health_check()

    assert result is False


def test_openai_provider_max_context_tokens(openai_provider: OpenAIProvider) -> None:
    """Test max_context_tokens property."""
    assert openai_provider.max_context_tokens == 128000


def test_openai_provider_max_context_tokens_custom() -> None:
    """Test max_context_tokens with custom context window."""
    config = ProviderConfig(
        provider_name="openai",
        api_key="test-key",
        enabled=True,
        priority=1,
        context_window=64000,
    )
    provider = OpenAIProvider(config)

    assert provider.max_context_tokens == 64000


@pytest.mark.asyncio
async def test_openai_provider_generate_uses_typed_messages(
    openai_provider: OpenAIProvider,
) -> None:
    """Test that generate() constructs typed message params for the OpenAI SDK."""
    from openai.types.chat.chat_completion_system_message_param import (
        ChatCompletionSystemMessageParam,
    )
    from openai.types.chat.chat_completion_user_message_param import (
        ChatCompletionUserMessageParam,
    )

    request = AIRequest(
        system_prompt="System instruction.",
        user_prompt="User question.",
        temperature=0.5,
        max_tokens=50,
    )

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Typed answer"
    mock_response.usage.prompt_tokens = 5
    mock_response.usage.completion_tokens = 3
    mock_response.usage.total_tokens = 8

    with patch.object(
        openai_provider._client.chat.completions,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_response

        await openai_provider.generate(request)

        call_kwargs = mock_create.call_args[1]
        messages = call_kwargs["messages"]
        assert isinstance(messages, list)
        assert messages[0] == ChatCompletionSystemMessageParam(
            role="system",
            content="System instruction.",
        )
        assert messages[1] == ChatCompletionUserMessageParam(
            role="user",
            content="User question.",
        )


@pytest.mark.asyncio
async def test_openai_provider_shutdown_closes_client(
    openai_provider: OpenAIProvider,
) -> None:
    """Test that shutdown() awaits client.close() when client exists."""
    mock_close = AsyncMock()
    openai_provider._client.close = mock_close

    await openai_provider.shutdown()

    mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_openai_provider_shutdown_without_client() -> None:
    """Test that shutdown() is safe when client is None."""
    config = ProviderConfig(
        provider_name="openai",
        api_key=None,
        enabled=True,
        priority=1,
    )
    provider = OpenAIProvider(config)

    await provider.shutdown()
