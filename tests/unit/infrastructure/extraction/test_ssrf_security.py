"""
Tests for redirect-based SSRF attacks in the article fetcher.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from ai_news_digest.infrastructure.extraction.ssrf_http_client import SsrfHttpArticleFetcher


def _make_client(handler) -> httpx.AsyncClient:
    """Create an AsyncClient with a MockTransport for testing."""
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


@pytest.mark.asyncio
async def test_redirect_to_localhost_rejected() -> None:
    """A redirect to localhost is rejected by SSRF validation."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"Location": "http://localhost/evil"},
            request=request,
        )

    client = _make_client(handler)
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.httpx.AsyncClient",
        return_value=client,
    ):
        fetcher = SsrfHttpArticleFetcher()
        result = await fetcher.fetch("https://example.com/page")

    assert result.failure_reason is not None
    assert "redirect" in result.failure_reason.lower()
    assert result.content == ""


@pytest.mark.asyncio
async def test_redirect_to_private_ip_rejected() -> None:
    """A redirect to a private IP is rejected."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"Location": "http://192.168.1.1/evil"},
            request=request,
        )

    client = _make_client(handler)
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.httpx.AsyncClient",
        return_value=client,
    ):
        fetcher = SsrfHttpArticleFetcher()
        result = await fetcher.fetch("https://example.com/page")

    assert result.failure_reason is not None
    assert "redirect" in result.failure_reason.lower()
    assert result.content == ""


@pytest.mark.asyncio
async def test_redirect_to_metadata_endpoint_rejected() -> None:
    """A redirect to the AWS metadata endpoint is rejected."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"Location": "http://169.254.169.254/latest/meta-data/"},
            request=request,
        )

    client = _make_client(handler)
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.httpx.AsyncClient",
        return_value=client,
    ):
        fetcher = SsrfHttpArticleFetcher()
        result = await fetcher.fetch("https://example.com/page")

    assert result.failure_reason is not None
    assert "redirect" in result.failure_reason.lower()
    assert result.content == ""


@pytest.mark.asyncio
async def test_redirect_loop_rejected() -> None:
    """A redirect chain exceeding max_redirects is rejected."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"Location": "https://example.com/loop"},
            request=request,
        )

    client = _make_client(handler)
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.httpx.AsyncClient",
        return_value=client,
    ):
        fetcher = SsrfHttpArticleFetcher()
        result = await fetcher.fetch("https://example.com/page")

    assert result.failure_reason is not None
    assert "exceeded the maximum number of redirects" in result.failure_reason
    assert result.content == ""


@pytest.mark.asyncio
async def test_redirect_to_unsupported_scheme_rejected() -> None:
    """A redirect to a non-http(s) scheme is rejected."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"Location": "file:///etc/passwd"},
            request=request,
        )

    client = _make_client(handler)
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.httpx.AsyncClient",
        return_value=client,
    ):
        fetcher = SsrfHttpArticleFetcher()
        result = await fetcher.fetch("https://example.com/page")

    assert result.failure_reason is not None
    assert "redirect" in result.failure_reason.lower()
    assert result.content == ""


@pytest.mark.asyncio
async def test_malformed_redirect_rejected() -> None:
    """A redirect without a Location header is rejected."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            request=request,
        )

    client = _make_client(handler)
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.httpx.AsyncClient",
        return_value=client,
    ):
        fetcher = SsrfHttpArticleFetcher()
        result = await fetcher.fetch("https://example.com/page")

    assert result.failure_reason is not None
    assert "redirect without a Location header" in result.failure_reason
    assert result.content == ""


@pytest.mark.asyncio
async def test_safe_redirect_accepted() -> None:
    """A safe redirect between public URLs is accepted."""

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.com/page":
            return httpx.Response(
                302,
                headers={"Location": "https://example.org/article"},
                request=request,
            )
        return httpx.Response(
            200,
            text="<html>Article content</html>",
            headers={"content-type": "text/html"},
            request=request,
        )

    client = _make_client(handler)
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.httpx.AsyncClient",
        return_value=client,
    ):
        fetcher = SsrfHttpArticleFetcher()
        result = await fetcher.fetch("https://example.com/page")

    assert result.failure_reason is None
    assert result.content == "<html>Article content</html>"
