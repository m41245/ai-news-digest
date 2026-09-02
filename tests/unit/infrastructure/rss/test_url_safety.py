"""
Unit tests for ``ai_news_digest.infrastructure.rss.url_safety``.

These tests exercise the outbound-URL safety boundary (SSRF protection) in
isolation.  They were previously embedded at the bottom of
``test_feedparser_fetcher.py``; they now live in a dedicated module so the
security-critical validation layer has visible, focused coverage.
"""

from __future__ import annotations

import pytest

from ai_news_digest.infrastructure.rss.url_safety import (
    MAX_REDIRECTS,
    SSRFValidationError,
    validate_rss_http_url,
)

# ----------------------------------------------------------------------
# Scheme validation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_rejects_non_http_scheme() -> None:
    """Only http and https schemes are permitted."""
    with pytest.raises(SSRFValidationError, match="scheme"):
        await validate_rss_http_url("file:///etc/passwd")
    with pytest.raises(SSRFValidationError, match="scheme"):
        await validate_rss_http_url("ftp://example.com/feed")
    with pytest.raises(SSRFValidationError, match="scheme"):
        await validate_rss_http_url("gopher://example.com/feed")
    with pytest.raises(SSRFValidationError, match="scheme"):
        await validate_rss_http_url("javascript:alert(1)")


@pytest.mark.asyncio
async def test_validate_rejects_empty_url() -> None:
    with pytest.raises(SSRFValidationError, match="empty"):
        await validate_rss_http_url("")
    with pytest.raises(SSRFValidationError, match="empty"):
        await validate_rss_http_url("   ")


@pytest.mark.asyncio
async def test_validate_rejects_missing_host() -> None:
    """A URL without a host is rejected."""
    with pytest.raises(SSRFValidationError, match="host"):
        await validate_rss_http_url("http://")


# ----------------------------------------------------------------------
# IP-literal blocking (no DNS resolution required)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_rejects_loopback_ipv4_literal() -> None:
    """127.0.0.0/8 loopback is blocked."""
    with pytest.raises(SSRFValidationError, match="host"):
        await validate_rss_http_url("http://127.0.0.1/feed")
    with pytest.raises(SSRFValidationError, match="host"):
        await validate_rss_http_url("http://127.1.2.3/feed")


@pytest.mark.asyncio
async def test_validate_rejects_loopback_ipv6_literal() -> None:
    """IPv6 loopback ::1 is blocked."""
    with pytest.raises(SSRFValidationError, match="host"):
        await validate_rss_http_url("http://[::1]/feed")


@pytest.mark.asyncio
async def test_validate_rejects_private_ip_literals() -> None:
    """RFC 1918 private ranges are blocked."""
    for ip in ("10.0.0.1", "172.16.0.1", "192.168.1.1"):
        with pytest.raises(SSRFValidationError, match="host"):
            await validate_rss_http_url(f"http://{ip}/feed")


@pytest.mark.asyncio
async def test_validate_rejects_link_local_address() -> None:
    """Link-local (169.254.0.0/16) addresses are blocked."""
    with pytest.raises(SSRFValidationError, match="host"):
        await validate_rss_http_url("http://169.254.1.1/feed")


@pytest.mark.asyncio
async def test_validate_rejects_multicast_address() -> None:
    """Multicast (224.0.0.0/4) addresses are blocked."""
    with pytest.raises(SSRFValidationError, match="host"):
        await validate_rss_http_url("http://224.0.0.1/feed")


@pytest.mark.asyncio
async def test_validate_rejects_unspecified_address() -> None:
    """The unspecified address 0.0.0.0 is blocked."""
    with pytest.raises(SSRFValidationError, match="host"):
        await validate_rss_http_url("http://0.0.0.0/feed")


@pytest.mark.asyncio
async def test_validate_rejects_ipv4_mapped_ipv6_private() -> None:
    """IPv4-mapped IPv6 private addresses are unwrapped and blocked."""
    with pytest.raises(SSRFValidationError, match="host"):
        await validate_rss_http_url("http://[::ffff:127.0.0.1]/feed")
    with pytest.raises(SSRFValidationError, match="host"):
        await validate_rss_http_url("http://[::ffff:10.0.0.1]/feed")


# ----------------------------------------------------------------------
# Hostname resolution checks
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_rejects_loopback_hostname() -> None:
    """The literal hostname 'localhost' resolves to a blocked address."""
    with pytest.raises(SSRFValidationError, match="host"):
        await validate_rss_http_url("http://localhost/feed.xml")


@pytest.mark.asyncio
async def test_validate_rejects_unresolvable_host() -> None:
    """Unresolvable hostnames fail closed."""
    with pytest.raises(SSRFValidationError, match="host"):
        await validate_rss_http_url("http://this-host-does-not-exist.invalid/feed")


@pytest.mark.asyncio
async def test_validate_accepts_public_url() -> None:
    """A well-known public hostname passes validation (DNS must resolve)."""
    result = await validate_rss_http_url("https://example.com/feed.xml")
    assert result == "https://example.com/feed.xml"


# ----------------------------------------------------------------------
# Module-level constants
# ----------------------------------------------------------------------


def test_max_redirects_constant() -> None:
    """MAX_REDIRECTS is a small bounded positive integer."""
    assert isinstance(MAX_REDIRECTS, int)
    assert MAX_REDIRECTS > 0
    assert MAX_REDIRECTS <= 20


__all__ = [
    "test_max_redirects_constant",
    "test_validate_accepts_public_url",
    "test_validate_rejects_empty_url",
    "test_validate_rejects_ipv4_mapped_ipv6_private",
    "test_validate_rejects_link_local_address",
    "test_validate_rejects_loopback_hostname",
    "test_validate_rejects_loopback_ipv4_literal",
    "test_validate_rejects_loopback_ipv6_literal",
    "test_validate_rejects_missing_host",
    "test_validate_rejects_multicast_address",
    "test_validate_rejects_non_http_scheme",
    "test_validate_rejects_private_ip_literals",
    "test_validate_rejects_unresolvable_host",
    "test_validate_rejects_unspecified_address",
]
