"""
Unit tests for SsrfHttpArticleFetcher.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from ai_news_digest.infrastructure.extraction import FetchResult, SsrfHttpArticleFetcher
from ai_news_digest.infrastructure.rss.url_safety import MAX_REDIRECTS, SSRFValidationError

_HTML_BODY = b"<html><body><p>Hello World</p></body></html>"


def _make_response(
    status_code: int = 200,
    headers: dict[str, str] | None = None,
    content: bytes = b"",
    url: str = "https://example.com/",
) -> httpx.Response:
    request = httpx.Request("GET", url)
    return httpx.Response(
        status_code=status_code,
        headers=headers or {},
        content=content,
        request=request,
    )


def _mock_transport(*responses: httpx.Response) -> httpx.MockTransport:
    calls = list(responses)
    call_index = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_index
        response = calls[call_index % len(calls)]
        call_index += 1
        return response

    return httpx.MockTransport(handler)


_original_async_client = httpx.AsyncClient


@contextmanager
def _with_mock_transport(*responses: httpx.Response) -> Generator[None, None, None]:
    mock_transport = _mock_transport(*responses)

    def side_effect(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        return _original_async_client(*args, transport=mock_transport, **kwargs)

    with patch("httpx.AsyncClient", side_effect=side_effect):
        yield


@contextmanager
def _with_mock_handler(
    handler: Any,
) -> Generator[None, None, None]:
    mock_transport = httpx.MockTransport(handler)

    def side_effect(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        return _original_async_client(*args, transport=mock_transport, **kwargs)

    with patch("httpx.AsyncClient", side_effect=side_effect):
        yield


@pytest.fixture
def fetcher() -> SsrfHttpArticleFetcher:
    return SsrfHttpArticleFetcher()


@pytest.mark.asyncio
async def test_fetch_success_html(fetcher: SsrfHttpArticleFetcher) -> None:
    """Successful fetch of simple HTML."""
    response = _make_response(
        status_code=200,
        headers={"content-type": "text/html; charset=utf-8"},
        content=_HTML_BODY,
        url="https://example.com/article",
    )

    with _with_mock_transport(response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == _HTML_BODY.decode("utf-8")
    assert result.status_code == 200
    assert result.content_type == "text/html; charset=utf-8"
    assert result.failure_reason is None
    assert result.redirected is False


@pytest.mark.asyncio
async def test_fetch_ssrf_localhost(fetcher: SsrfHttpArticleFetcher) -> None:
    """SSRF rejection of localhost."""
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        side_effect=SSRFValidationError("Feed URL host 'localhost' is not permitted."),
    ):
        result = await fetcher.fetch("http://localhost/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None
    assert "localhost" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_ssrf_127_0_0_1(fetcher: SsrfHttpArticleFetcher) -> None:
    """SSRF rejection of 127.0.0.1."""
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        side_effect=SSRFValidationError("Feed URL host '127.0.0.1' is not permitted."),
    ):
        result = await fetcher.fetch("http://127.0.0.1/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None


@pytest.mark.asyncio
async def test_fetch_ssrf_private_ip_10(fetcher: SsrfHttpArticleFetcher) -> None:
    """SSRF rejection of private IP (10.x)."""
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        side_effect=SSRFValidationError("Feed URL host '10.0.0.1' is not permitted."),
    ):
        result = await fetcher.fetch("http://10.0.0.1/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None


@pytest.mark.asyncio
async def test_fetch_ssrf_private_ip_172(fetcher: SsrfHttpArticleFetcher) -> None:
    """SSRF rejection of private IP (172.16.x)."""
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        side_effect=SSRFValidationError(
            "Feed URL host '172.16.0.1' is not permitted."
        ),
    ):
        result = await fetcher.fetch("http://172.16.0.1/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None


@pytest.mark.asyncio
async def test_fetch_ssrf_private_ip_192(fetcher: SsrfHttpArticleFetcher) -> None:
    """SSRF rejection of private IP (192.168.x)."""
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        side_effect=SSRFValidationError(
            "Feed URL host '192.168.1.1' is not permitted."
        ),
    ):
        result = await fetcher.fetch("http://192.168.1.1/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None


@pytest.mark.asyncio
async def test_fetch_ssrf_link_local(fetcher: SsrfHttpArticleFetcher) -> None:
    """SSRF rejection of link-local (169.254.x)."""
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        side_effect=SSRFValidationError(
            "Feed URL host '169.254.1.1' is not permitted."
        ),
    ):
        result = await fetcher.fetch("http://169.254.1.1/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None


@pytest.mark.asyncio
async def test_fetch_ssrf_ipv6_loopback(fetcher: SsrfHttpArticleFetcher) -> None:
    """SSRF rejection of loopback IPv6 [::1]."""
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        side_effect=SSRFValidationError("Feed URL host '::1' is not permitted."),
    ):
        result = await fetcher.fetch("http://[::1]/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None


@pytest.mark.asyncio
async def test_fetch_ssrf_ipv4_mapped_ipv6(fetcher: SsrfHttpArticleFetcher) -> None:
    """SSRF rejection of IPv4-mapped IPv6 [::ffff:127.0.0.1]."""
    with patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        side_effect=SSRFValidationError(
            "Feed URL host '::ffff:127.0.0.1' is not permitted."
        ),
    ):
        result = await fetcher.fetch("http://[::ffff:127.0.0.1]/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None


@pytest.mark.asyncio
async def test_fetch_redirect_to_localhost_rejected(
    fetcher: SsrfHttpArticleFetcher,
) -> None:
    """SSRF rejection of redirect to localhost."""
    call_count = 0

    async def mock_validate(raw: str) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return raw
        raise SSRFValidationError(
            f"Feed URL host '{httpx.URL(raw).host}' is not permitted."
        )

    redirect_response = _make_response(
        status_code=302,
        headers={"location": "http://localhost/admin"},
        url="https://example.com/article",
    )

    with _with_mock_transport(redirect_response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        side_effect=mock_validate,
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None
    assert "localhost" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_redirect_to_private_ip_rejected(
    fetcher: SsrfHttpArticleFetcher,
) -> None:
    """SSRF rejection of redirect to private IP."""
    call_count = 0

    async def mock_validate(raw: str) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return raw
        raise SSRFValidationError(
            f"Feed URL host '{httpx.URL(raw).host}' is not permitted."
        )

    redirect_response = _make_response(
        status_code=302,
        headers={"location": "http://192.168.1.1/internal"},
        url="https://example.com/article",
    )

    with _with_mock_transport(redirect_response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        side_effect=mock_validate,
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None
    assert "192.168.1.1" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_redirect_loop_exceeds_max(
    fetcher: SsrfHttpArticleFetcher,
) -> None:
    """Redirect loop exceeding max_redirects."""
    redirect_response = _make_response(
        status_code=302,
        headers={"location": "https://example.com/loop"},
        url="https://example.com/article",
    )

    with _with_mock_transport(redirect_response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None
    assert "exceeded the maximum number of redirects" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_timeout(fetcher: SsrfHttpArticleFetcher) -> None:
    """Timeout handling."""

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Timed out!")

    with _with_mock_handler(handler), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await SsrfHttpArticleFetcher(timeout=0.001).fetch(
            "https://example.com/article"
        )

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None
    assert "Timed out" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_http_404(fetcher: SsrfHttpArticleFetcher) -> None:
    """HTTP 404."""
    response = _make_response(
        status_code=404,
        headers={"content-type": "text/html"},
        content=b"Not Found",
        url="https://example.com/article",
    )

    with _with_mock_transport(response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.status_code == 404
    assert result.failure_reason is not None
    assert "HTTP 404" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_http_403(fetcher: SsrfHttpArticleFetcher) -> None:
    """HTTP 403."""
    response = _make_response(
        status_code=403,
        headers={"content-type": "text/html"},
        content=b"Forbidden",
        url="https://example.com/article",
    )

    with _with_mock_transport(response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.status_code == 403
    assert result.failure_reason is not None
    assert "HTTP 403" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_http_500(fetcher: SsrfHttpArticleFetcher) -> None:
    """HTTP 500."""
    response = _make_response(
        status_code=500,
        headers={"content-type": "text/html"},
        content=b"Server Error",
        url="https://example.com/article",
    )

    with _with_mock_transport(response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.status_code == 500
    assert result.failure_reason is not None
    assert "HTTP 500" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_unsupported_content_type_pdf(
    fetcher: SsrfHttpArticleFetcher,
) -> None:
    """Unsupported content type (application/pdf)."""
    response = _make_response(
        status_code=200,
        headers={"content-type": "application/pdf"},
        content=b"%PDF-1.4...",
        url="https://example.com/article",
    )

    with _with_mock_transport(response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.status_code == 200
    assert result.failure_reason is not None
    assert "unsupported content type" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_oversized_content_length(fetcher: SsrfHttpArticleFetcher) -> None:
    """Oversized response (Content-Length header too large)."""
    oversized_body = b"x" * 100
    response = _make_response(
        status_code=200,
        headers={"content-type": "text/html", "content-length": "10000000"},
        content=oversized_body,
        url="https://example.com/article",
    )

    with _with_mock_transport(response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.status_code == 200
    assert result.failure_reason is not None
    assert "exceeds the maximum allowed size" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_oversized_streamed_body(fetcher: SsrfHttpArticleFetcher) -> None:
    """Oversized response (streamed body too large)."""
    large_body = b"x" * (fetcher._max_response_bytes + 1024)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=large_body,
            request=request,
        )

    with _with_mock_handler(handler), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.status_code == 200
    assert result.failure_reason is not None
    assert "exceeds the maximum allowed size" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_connection_failure(fetcher: SsrfHttpArticleFetcher) -> None:
    """Connection failure."""

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    with _with_mock_handler(handler), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None
    assert "Failed to fetch article" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_malformed_redirect_missing_location(
    fetcher: SsrfHttpArticleFetcher,
) -> None:
    """Malformed redirect (missing Location header)."""
    response = _make_response(
        status_code=302,
        headers={},
        content=b"",
        url="https://example.com/article",
    )

    with _with_mock_transport(response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.status_code == 302
    assert result.failure_reason is not None
    assert "redirect without a Location header" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_redirect_to_unsupported_scheme(
    fetcher: SsrfHttpArticleFetcher,
) -> None:
    """Redirect to unsupported scheme (file://)."""
    call_count = 0

    async def mock_validate(raw: str) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return raw
        raise SSRFValidationError("Feed URL scheme must be http or https.")

    redirect_response = _make_response(
        status_code=302,
        headers={"location": "file:///etc/passwd"},
        url="https://example.com/article",
    )

    with _with_mock_transport(redirect_response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        side_effect=mock_validate,
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None
    assert "http or https" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_success_xhtml(fetcher: SsrfHttpArticleFetcher) -> None:
    """Successful fetch of XHTML."""
    xhtml = (
        b'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml">'
        b"<body><p>XHTML</p></body></html>"
    )
    response = _make_response(
        status_code=200,
        headers={"content-type": "application/xhtml+xml"},
        content=xhtml,
        url="https://example.com/article",
    )

    with _with_mock_transport(response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == xhtml.decode("utf-8")
    assert result.status_code == 200
    assert result.failure_reason is None


@pytest.mark.asyncio
async def test_fetch_success_text_plain(fetcher: SsrfHttpArticleFetcher) -> None:
    """Successful fetch of text/plain."""
    text_body = b"Hello World plain text"
    response = _make_response(
        status_code=200,
        headers={"content-type": "text/plain"},
        content=text_body,
        url="https://example.com/article",
    )

    with _with_mock_transport(response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == text_body.decode("utf-8")
    assert result.status_code == 200
    assert result.failure_reason is None


@pytest.mark.asyncio
async def test_fetch_redirects_once(fetcher: SsrfHttpArticleFetcher) -> None:
    """Single redirect is followed successfully."""
    redirect_response = _make_response(
        status_code=302,
        headers={"location": "https://example.com/final"},
        url="https://example.com/article",
    )
    final_response = _make_response(
        status_code=200,
        headers={"content-type": "text/html"},
        content=_HTML_BODY,
        url="https://example.com/final",
    )

    with _with_mock_transport(redirect_response, final_response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        side_effect=[
            "https://example.com/article",
            "https://example.com/final",
        ],
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == _HTML_BODY.decode("utf-8")
    assert result.status_code == 200
    assert result.redirected is True
    assert result.failure_reason is None


@pytest.mark.asyncio
async def test_fetch_uses_default_parameters() -> None:
    """Default parameters are applied correctly."""
    fetcher = SsrfHttpArticleFetcher()
    assert fetcher._timeout == 20.0
    assert fetcher._max_response_bytes == 5_000_000
    assert fetcher._max_redirects == MAX_REDIRECTS


@pytest.mark.asyncio
async def test_fetch_image_content_type_rejected(
    fetcher: SsrfHttpArticleFetcher,
) -> None:
    """Image content types are rejected."""
    response = _make_response(
        status_code=200,
        headers={"content-type": "image/png"},
        content=b"PNGDATA",
        url="https://example.com/article",
    )

    with _with_mock_transport(response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content == ""
    assert result.failure_reason is not None
    assert "unsupported content type" in result.failure_reason


@pytest.mark.asyncio
async def test_fetch_decode_error_handled(fetcher: SsrfHttpArticleFetcher) -> None:
    """Decode errors are handled gracefully with utf-8 fallback."""
    invalid_utf8 = b"\xff\xfe"
    response = _make_response(
        status_code=200,
        headers={"content-type": "text/html"},
        content=invalid_utf8,
        url="https://example.com/article",
    )

    with _with_mock_transport(response), patch(
        "ai_news_digest.infrastructure.extraction.ssrf_http_client.validate_rss_http_url",
        new_callable=AsyncMock,
        return_value="https://example.com/article",
    ):
        result = await fetcher.fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.content != ""
    assert result.status_code == 200
    assert result.failure_reason is None
