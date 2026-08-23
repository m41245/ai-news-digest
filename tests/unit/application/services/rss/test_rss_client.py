"""
Unit tests for RSSClient.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_news_digest.application.services.rss.exceptions import (
    RSSConnectionError,
    RSSInvalidResponseError,
    RSSRequestError,
    RSSTimeoutError,
)
from ai_news_digest.application.services.rss.rss_client import RSSClient


@pytest.fixture
def rss_client() -> RSSClient:
    """Create an RSSClient instance for testing."""
    return RSSClient(
        timeout=5.0,
        max_retries=2,
        backoff_factor=0.5,
    )


async def test_rss_client_init() -> None:
    """Test RSSClient initialization."""
    client = RSSClient(
        timeout=10.0,
        max_retries=3,
        backoff_factor=1.0,
        user_agent="Custom Agent",
    )

    assert client._timeout == 10.0
    assert client._max_retries == 3
    assert client._backoff_factor == 1.0
    assert client._user_agent == "Custom Agent"


async def test_rss_client_context_manager(rss_client: RSSClient) -> None:
    """Test RSSClient as async context manager."""
    async with rss_client as client:
        assert client is rss_client
    # Client should be closed after exiting context


async def test_rss_client_validate_content_type_valid() -> None:
    """Test content type validation with valid types."""
    valid_types = [
        "application/rss+xml",
        "application/atom+xml",
        "application/xml",
        "text/xml",
        "application/xhtml+xml",
        "text/plain",
    ]

    for content_type in valid_types:
        RSSClient._validate_content_type(content_type)  # Should not raise


async def test_rss_client_validate_content_type_invalid() -> None:
    """Test content type validation with invalid types."""
    with pytest.raises(RSSInvalidResponseError, match="Content-Type"):
        RSSClient._validate_content_type("application/json")

    with pytest.raises(RSSInvalidResponseError, match="Content-Type"):
        RSSClient._validate_content_type("text/html")


async def test_rss_client_fetch_timeout_error(rss_client: RSSClient) -> None:
    """Test RSSClient fetch with timeout error."""
    with patch.object(rss_client._client, "get") as mock_get:
        import httpx

        mock_get.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(RSSTimeoutError, match="Timed out"):
            await rss_client.fetch("https://example.com/feed.xml")


async def test_rss_client_fetch_connection_error(rss_client: RSSClient) -> None:
    """Test RSSClient fetch with connection error."""
    with patch.object(rss_client._client, "get") as mock_get:
        import httpx

        mock_get.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(RSSConnectionError, match="Unable to connect"):
            await rss_client.fetch("https://example.com/feed.xml")


async def test_rss_client_fetch_http_status_error(rss_client: RSSClient) -> None:
    """Test RSSClient fetch with HTTP status error."""
    with patch.object(rss_client._client, "get") as mock_get:
        import httpx

        response = MagicMock()
        response.status_code = 404
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=response,
        )
        mock_get.return_value = response

        with pytest.raises(RSSRequestError, match="HTTP 404"):
            await rss_client.fetch("https://example.com/feed.xml")


async def test_rss_client_fetch_http_error(rss_client: RSSClient) -> None:
    """Test RSSClient fetch with generic HTTP error."""
    with patch.object(rss_client._client, "get") as mock_get:
        import httpx

        mock_get.side_effect = httpx.HTTPError("Generic HTTP error")

        with pytest.raises(RSSRequestError, match="Unexpected HTTP error"):
            await rss_client.fetch("https://example.com/feed.xml")


async def test_rss_client_fetch_invalid_content_type(rss_client: RSSClient) -> None:
    """Test RSSClient fetch with invalid content type."""
    with patch.object(rss_client._client, "get") as mock_get:
        response = MagicMock()
        response.status_code = 200
        response.headers = {"Content-Type": "application/json"}
        response.text = "<rss></rss>"
        response.raise_for_status = MagicMock()
        mock_get.return_value = response

        with pytest.raises(RSSInvalidResponseError, match="Content-Type"):
            await rss_client.fetch("https://example.com/feed.xml")


async def test_rss_client_fetch_success(rss_client: RSSClient) -> None:
    """Test RSSClient fetch success."""
    with patch.object(rss_client._client, "get") as mock_get:
        response = MagicMock()
        response.status_code = 200
        response.headers = {"Content-Type": "application/rss+xml"}
        response.text = "<rss><channel><title>Test</title></channel></rss>"
        response.raise_for_status = MagicMock()
        mock_get.return_value = response

        result = await rss_client.fetch("https://example.com/feed.xml")

        assert result == "<rss><channel><title>Test</title></channel></rss>"
        mock_get.assert_called_once()


async def test_rss_client_fetch_with_custom_headers(rss_client: RSSClient) -> None:
    """Test RSSClient fetch with custom headers."""
    with patch.object(rss_client._client, "get") as mock_get:
        response = MagicMock()
        response.status_code = 200
        response.headers = {"Content-Type": "application/rss+xml"}
        response.text = "<rss></rss>"
        response.raise_for_status = MagicMock()
        mock_get.return_value = response

        await rss_client.fetch(
            "https://example.com/feed.xml",
            headers={"Authorization": "Bearer token"},
        )

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args.kwargs
        assert "Authorization" in call_kwargs["headers"]


async def test_rss_client_close(rss_client: RSSClient) -> None:
    """Test RSSClient close method."""
    with patch.object(rss_client._client, "aclose", new_callable=AsyncMock) as mock_close:
        await rss_client.close()
        mock_close.assert_called_once()
