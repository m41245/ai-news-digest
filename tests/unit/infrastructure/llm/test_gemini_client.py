"""
Unit tests for GeminiProvider.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.application.ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidResponseError,
    AIRateLimitError,
    AITimeoutError,
    AITransientError,
)
from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponseFormat,
)
from ai_news_digest.infrastructure.llm.gemini_client import GeminiProvider


@pytest.fixture
def provider_config() -> ProviderConfig:
    """Create a ProviderConfig for testing."""
    return ProviderConfig(
        provider_name="gemini",
        api_key="test-api-key",
        enabled=True,
        priority=3,
        model="gemini-2.0-flash",
        timeout=30,
        max_retries=3,
    )


@pytest.fixture
def gemini_provider(provider_config: ProviderConfig) -> GeminiProvider:
    """Create a GeminiProvider instance."""
    return GeminiProvider(provider_config)


def test_gemini_provider_initialization(provider_config: ProviderConfig) -> None:
    """Test GeminiProvider initialization."""
    provider = GeminiProvider(provider_config)

    assert provider.provider_name == "gemini"
    assert provider.model_name == "gemini-2.0-flash"
    assert provider.priority() == 3
    assert provider.supports_streaming is False
    assert provider.supports_json_mode is True
    assert provider.supports_vision is True


def test_gemini_provider_initialization_without_api_key() -> None:
    """Test GeminiProvider initialization without API key."""
    config = ProviderConfig(
        provider_name="gemini",
        api_key=None,
        enabled=True,
        priority=3,
    )
    provider = GeminiProvider(config)

    assert provider._config.api_key is None


@pytest.mark.asyncio
async def test_gemini_provider_available(gemini_provider: GeminiProvider) -> None:
    """Test available method."""
    assert await gemini_provider.available() is True


@pytest.mark.asyncio
async def test_gemini_provider_not_available_without_key() -> None:
    """Test available method when API key is not configured."""
    config = ProviderConfig(
        provider_name="gemini",
        api_key=None,
        enabled=True,
        priority=3,
    )
    provider = GeminiProvider(config)

    assert await provider.available() is False


@pytest.mark.asyncio
async def test_gemini_provider_generate_success(gemini_provider: GeminiProvider) -> None:
    """Test successful AI generation."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Summary text"},
                    ],
                },
            },
        ],
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 5,
            "totalTokenCount": 15,
        },
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = await gemini_provider.generate(request)

        assert result.provider == "gemini"
        assert result.model == "gemini-2.0-flash"
        assert result.content == "Summary text"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
        assert result.usage.total_tokens == 15
        assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_gemini_provider_generate_with_json_mode(gemini_provider: GeminiProvider) -> None:
    """Test AI generation with JSON mode."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
        response_format=AIResponseFormat.JSON,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": '{"summary": "text"}'},
                    ],
                },
            },
        ],
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 5,
            "totalTokenCount": 15,
        },
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        await gemini_provider.generate(request)

        call_kwargs = mock_client.post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["generationConfig"]["responseMimeType"] == "application/json"


@pytest.mark.asyncio
async def test_gemini_provider_generate_without_api_key() -> None:
    """Test generate raises error when API key is not configured."""
    config = ProviderConfig(
        provider_name="gemini",
        api_key=None,
        enabled=True,
        priority=3,
    )
    provider = GeminiProvider(config)

    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with pytest.raises(AIConfigurationError, match="Gemini API key not configured"):
        await provider.generate(request)


@pytest.mark.asyncio
async def test_gemini_provider_generate_api_error(gemini_provider: GeminiProvider) -> None:
    """Test generate handles API errors by mapping them to the error model."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500, text="Internal Server Error"),
        )
        mock_client_cls.return_value = mock_client

        with pytest.raises(AITransientError, match="Gemini server error"):
            await gemini_provider.generate(request)


@pytest.mark.asyncio
async def test_gemini_provider_generate_auth_error(gemini_provider: GeminiProvider) -> None:
    """Authentication errors are mapped and not retried."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=MagicMock(status_code=401, text="Invalid API key"),
        )
        mock_client_cls.return_value = mock_client

        with pytest.raises(AIAuthenticationError, match="Gemini authentication failed"):
            await gemini_provider.generate(request)


@pytest.mark.asyncio
async def test_gemini_provider_generate_rate_limit_error(gemini_provider: GeminiProvider) -> None:
    """Rate limit errors are mapped and not retried."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "Rate Limited",
            request=MagicMock(),
            response=MagicMock(status_code=429, text="Rate limit exceeded"),
        )
        mock_client_cls.return_value = mock_client

        with pytest.raises(AIRateLimitError, match="Gemini rate limit exceeded"):
            await gemini_provider.generate(request)


@pytest.mark.asyncio
async def test_gemini_provider_generate_timeout_error(gemini_provider: GeminiProvider) -> None:
    """Timeout errors are mapped and not retried."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
        mock_client_cls.return_value = mock_client

        with pytest.raises(AITimeoutError, match="Gemini request timed out"):
            await gemini_provider.generate(request)


@pytest.mark.asyncio
async def test_gemini_provider_generate_empty_candidates(gemini_provider: GeminiProvider) -> None:
    """Test response with empty candidates raises error."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"candidates": []}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        with pytest.raises(
            AIInvalidResponseError,
            match="Gemini API returned an empty candidates list",
        ):
            await gemini_provider.generate(request)


@pytest.mark.asyncio
async def test_gemini_provider_generate_missing_text(gemini_provider: GeminiProvider) -> None:
    """Test response with missing text content raises error."""
    request = AIRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Summarize this text.",
        temperature=0.7,
        max_tokens=100,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {},
                    ],
                },
            },
        ],
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        with pytest.raises(
            AIInvalidResponseError,
            match="Gemini response did not contain any text content",
        ):
            await gemini_provider.generate(request)


@pytest.mark.asyncio
async def test_gemini_provider_health_check_success(gemini_provider: GeminiProvider) -> None:
    """Test successful health check."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = await gemini_provider.health_check()

        assert result is True


@pytest.mark.asyncio
async def test_gemini_provider_health_check_failure(gemini_provider: GeminiProvider) -> None:
    """Test health check on failure."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.side_effect = Exception("Connection error")
        mock_client_cls.return_value = mock_client

        result = await gemini_provider.health_check()

        assert result is False


@pytest.mark.asyncio
async def test_gemini_provider_health_check_without_key() -> None:
    """Test health check when API key is not configured."""
    config = ProviderConfig(
        provider_name="gemini",
        api_key=None,
        enabled=True,
        priority=3,
    )
    provider = GeminiProvider(config)

    result = await provider.health_check()

    assert result is False


def test_gemini_provider_max_context_tokens(gemini_provider: GeminiProvider) -> None:
    """Test max_context_tokens property."""
    assert gemini_provider.max_context_tokens == 1048576


def test_gemini_provider_max_context_tokens_custom() -> None:
    """Test max_context_tokens with custom context window."""
    config = ProviderConfig(
        provider_name="gemini",
        api_key="test-key",
        enabled=True,
        priority=3,
        context_window=64000,
    )
    provider = GeminiProvider(config)

    assert provider.max_context_tokens == 64000


__all__ = [
    "test_gemini_provider_available",
    "test_gemini_provider_generate_api_error",
    "test_gemini_provider_generate_auth_error",
    "test_gemini_provider_generate_empty_candidates",
    "test_gemini_provider_generate_missing_text",
    "test_gemini_provider_generate_rate_limit_error",
    "test_gemini_provider_generate_success",
    "test_gemini_provider_generate_timeout_error",
    "test_gemini_provider_generate_with_json_mode",
    "test_gemini_provider_generate_without_api_key",
    "test_gemini_provider_health_check_failure",
    "test_gemini_provider_health_check_success",
    "test_gemini_provider_health_check_without_key",
    "test_gemini_provider_initialization",
    "test_gemini_provider_initialization_without_api_key",
    "test_gemini_provider_max_context_tokens",
    "test_gemini_provider_max_context_tokens_custom",
    "test_gemini_provider_not_available_without_key",
]
