"""
Unit tests for AnthropicProvider.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.application.ai.models import AIRequest
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.infrastructure.llm.anthropic_client import AnthropicProvider


@pytest.fixture
def provider_config() -> ProviderConfig:
    """Create a ProviderConfig for testing."""
    return ProviderConfig(
        provider_name="anthropic",
        api_key="test-api-key",
        enabled=True,
        priority=2,
        model="claude-3-5-sonnet-20241022",
        timeout=30,
        max_retries=3,
    )


@pytest.fixture
def anthropic_provider(provider_config: ProviderConfig) -> AnthropicProvider:
    """Create an AnthropicProvider instance."""
    return AnthropicProvider(provider_config)


def test_anthropic_provider_initialization(provider_config: ProviderConfig) -> None:
    """Test AnthropicProvider initialization."""
    provider = AnthropicProvider(provider_config)

    assert provider.provider_name == "anthropic"
    assert provider.model_name == "claude-3-5-sonnet-20241022"
    assert provider.priority() == 2
    assert provider.supports_streaming is True
    assert provider.supports_json_mode is False
    assert provider.supports_vision is True


def test_anthropic_provider_initialization_without_api_key() -> None:
    """Test AnthropicProvider initialization without API key."""
    config = ProviderConfig(
        provider_name="anthropic",
        api_key=None,
        enabled=True,
        priority=2,
    )
    provider = AnthropicProvider(config)

    assert provider._client is None


@pytest.mark.asyncio
async def test_anthropic_provider_available(anthropic_provider: AnthropicProvider) -> None:
    """Test available method."""
    assert await anthropic_provider.available() is True


@pytest.mark.asyncio
async def test_anthropic_provider_not_available_without_client() -> None:
    """Test available method when client is not configured."""
    config = ProviderConfig(
        provider_name="anthropic",
        api_key=None,
        enabled=True,
        priority=2,
    )
    provider = AnthropicProvider(config)

    assert await provider.available() is False


@pytest.mark.asyncio
async def test_anthropic_provider_generate_success(anthropic_provider: AnthropicProvider) -> None:
    """Test successful AI generation."""
    from anthropic.types.text_block import TextBlock

    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    text_block = TextBlock(text="Summary text", type="text")
    mock_response = MagicMock()
    mock_response.content = [text_block]
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5

    with patch.object(
        anthropic_provider._client.messages, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        result = await anthropic_provider.generate(request)

        assert result.provider == "anthropic"
        assert result.model == "claude-3-5-sonnet-20241022"
        assert result.content == "Summary text"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
        assert result.usage.total_tokens == 15
        assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_anthropic_provider_generate_without_client() -> None:
    """Test generate raises error when client is not configured."""
    config = ProviderConfig(
        provider_name="anthropic",
        api_key=None,
        enabled=True,
        priority=2,
    )
    provider = AnthropicProvider(config)

    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with pytest.raises(ExternalServiceError, match="Anthropic client not configured"):
        await provider.generate(request)


@pytest.mark.asyncio
async def test_anthropic_provider_generate_api_error(anthropic_provider: AnthropicProvider) -> None:
    """Test generate handles API errors by mapping them to the error model."""
    from ai_news_digest.application.ai.errors import AITransientError

    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with patch.object(
        anthropic_provider._client.messages, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = Exception("API Error")

        with pytest.raises(AITransientError, match="Anthropic request failed"):
            await anthropic_provider.generate(request)


@pytest.mark.asyncio
async def test_anthropic_provider_generate_auth_error(
    anthropic_provider: AnthropicProvider,
) -> None:
    """Authentication errors are mapped and not retried."""
    from anthropic import AuthenticationError as AnthropicAuthError

    from ai_news_digest.application.ai.errors import AIAuthenticationError

    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with patch.object(
        anthropic_provider._client.messages, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = AnthropicAuthError(
            message="Invalid API key",
            response=MagicMock(),
            body=None,
        )

        with pytest.raises(AIAuthenticationError, match="authentication failed"):
            await anthropic_provider.generate(request)


@pytest.mark.asyncio
async def test_anthropic_provider_health_check_success(
    anthropic_provider: AnthropicProvider,
) -> None:
    """Test successful health check."""
    mock_response = MagicMock()
    mock_content_block = MagicMock()
    mock_content_block.text = "test"
    mock_response.content = [mock_content_block]

    with patch.object(
        anthropic_provider._client.messages, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        result = await anthropic_provider.health_check()

        assert result is True


@pytest.mark.asyncio
async def test_anthropic_provider_health_check_failure(
    anthropic_provider: AnthropicProvider,
) -> None:
    """Test health check on failure."""
    with patch.object(
        anthropic_provider._client.messages, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = Exception("Connection error")

        result = await anthropic_provider.health_check()

        assert result is False


@pytest.mark.asyncio
async def test_anthropic_provider_health_check_without_client() -> None:
    """Test health check when client is not configured."""
    config = ProviderConfig(
        provider_name="anthropic",
        api_key=None,
        enabled=True,
        priority=2,
    )
    provider = AnthropicProvider(config)

    result = await provider.health_check()

    assert result is False


def test_anthropic_provider_max_context_tokens(anthropic_provider: AnthropicProvider) -> None:
    """Test max_context_tokens property."""
    assert anthropic_provider.max_context_tokens == 200000


def test_anthropic_provider_max_context_tokens_custom() -> None:
    """Test max_context_tokens with custom context window."""
    config = ProviderConfig(
        provider_name="anthropic",
        api_key="test-key",
        enabled=True,
        priority=2,
        context_window=100000,
    )
    provider = AnthropicProvider(config)

    assert provider.max_context_tokens == 100000


@pytest.mark.asyncio
async def test_anthropic_provider_generate_with_text_block(
    anthropic_provider: AnthropicProvider,
) -> None:
    """Test successful generation with an actual SDK TextBlock."""
    from anthropic.types.text_block import TextBlock

    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    text_block = TextBlock(text="Summary text", type="text")
    mock_response = MagicMock()
    mock_response.content = [text_block]
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5

    mock_create = patch.object(
        anthropic_provider._client.messages,
        "create",
        new_callable=AsyncMock,
    )
    with mock_create as mocked_create:
        mocked_create.return_value = mock_response

        result = await anthropic_provider.generate(request)

        assert result.content == "Summary text"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
        assert result.usage.total_tokens == 15


@pytest.mark.asyncio
async def test_anthropic_provider_generate_with_tool_use_block(
    anthropic_provider: AnthropicProvider,
) -> None:
    """Test that ToolUseBlock does not cause AttributeError."""
    from anthropic.types.text_block import TextBlock
    from anthropic.types.tool_use_block import ToolUseBlock

    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Use a tool.",
        temperature=0.7,
        max_tokens=100,
    )

    tool_block = ToolUseBlock(
        id="tool-1",
        input={"query": "test"},
        name="search",
        type="tool_use",
    )
    text_block = TextBlock(text="Tool result text", type="text")
    mock_response = MagicMock()
    mock_response.content = [tool_block, text_block]
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5

    mock_create = patch.object(
        anthropic_provider._client.messages,
        "create",
        new_callable=AsyncMock,
    )
    with mock_create as mocked_create:
        mocked_create.return_value = mock_response

        result = await anthropic_provider.generate(request)

        assert result.content == "Tool result text"


@pytest.mark.asyncio
async def test_anthropic_provider_generate_only_tool_use_block(
    anthropic_provider: AnthropicProvider,
) -> None:
    """Test response containing only ToolUseBlock raises ExternalServiceError."""
    from anthropic.types.tool_use_block import ToolUseBlock

    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Use a tool.",
        temperature=0.7,
        max_tokens=100,
    )

    tool_block = ToolUseBlock(
        id="tool-1",
        input={"query": "test"},
        name="search",
        type="tool_use",
    )
    mock_response = MagicMock()
    mock_response.content = [tool_block]
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5

    mock_create = patch.object(
        anthropic_provider._client.messages,
        "create",
        new_callable=AsyncMock,
    )
    with mock_create as mocked_create:
        mocked_create.return_value = mock_response

        with pytest.raises(
            ExternalServiceError,
            match="Anthropic response did not contain any text content",
        ):
            await anthropic_provider.generate(request)


@pytest.mark.asyncio
async def test_anthropic_provider_generate_empty_content(
    anthropic_provider: AnthropicProvider,
) -> None:
    """Test response with empty content raises ExternalServiceError."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    mock_response = MagicMock()
    mock_response.content = []
    mock_response.usage.input_tokens = 0
    mock_response.usage.output_tokens = 0

    mock_create = patch.object(
        anthropic_provider._client.messages,
        "create",
        new_callable=AsyncMock,
    )
    with mock_create as mocked_create:
        mocked_create.return_value = mock_response

        with pytest.raises(
            ExternalServiceError,
            match="Anthropic response did not contain any text content",
        ):
            await anthropic_provider.generate(request)
