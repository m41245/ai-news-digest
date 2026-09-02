"""SSRF-safe outbound URL validation for RSS/Atom fetching.

RSS feed URLs are external input persisted through the admin API and later
fetched by workers, so they form the application's outbound network boundary.

This module enforces a production-safe boundary:

* Only ``http`` and ``https`` schemes are permitted.
* Hosts must resolve to globally routable addresses. Loopback, link-local,
  private (RFC 1918 / unique local), reserved, multicast, unspecified and
  IPv4-mapped private addresses are rejected.
* Hostnames that cannot be resolved are rejected (fail-closed): the fetch
  layer must not retry a destination it could not verify.
* Every redirect hop is re-validated before it is followed, so a public feed
  cannot redirect the connection to an internal address.

The boundary is intentionally strict about *destinations* while remaining
permissive for legitimate public feeds: any public hostname resolving to a
public address passes normally.

Note on DNS rebinding: validation resolves the hostname before the HTTP
request. A malicious authoritative DNS server could in principle return a
public address during validation and a private address during the fetch.
For a fully rebinding-immune boundary, egress controls (network policy /
explicit proxy) are required at the platform layer; the per-hop re-validation
here removes the most common SSRF vectors (scheme confusion, IP-literal
targets, and redirect smuggling).
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

_ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})

# Maximum redirect hops the fetcher will follow, each hop re-validated.
MAX_REDIRECTS = 5


class SSRFValidationError(Exception):
    """Raised when a feed URL fails the outbound safety boundary."""


async def validate_rss_http_url(raw: str) -> str:
    """Validate *raw* for safe outbound fetching and return it unchanged.

    Raises:
        SSRFValidationError: If the URL is empty, uses a disallowed scheme,
            has no host, resolves to a blocked address, or cannot resolve.
    """
    cleaned = (raw or "").strip()
    if not cleaned:
        raise SSRFValidationError("Feed URL must not be empty.")

    parts = urlsplit(cleaned)
    if parts.scheme.lower() not in _ALLOWED_SCHEMES:
        raise SSRFValidationError("Feed URL scheme must be http or https.")

    host = parts.hostname
    if not host:
        raise SSRFValidationError("Feed URL must include a host.")

    if not await _host_is_safe(host):
        raise SSRFValidationError(f"Feed URL host '{host}' is not permitted.")

    return cleaned


async def _host_is_safe(host: str) -> bool:
    """Return True only when *host* is verifiably a public destination."""
    literal = _parse_ip_literal(host)
    if literal is not None:
        return not _ip_is_blocked(literal)

    resolved = await _resolve_host_ips(host)
    if not resolved:
        # Fail closed: we could not verify the destination.
        return False

    return all(not _ip_is_blocked(ip) for ip in resolved)


def _parse_ip_literal(host: str) -> str | None:
    """Return the stripped host if it is an IP literal, else None."""
    candidate = host.strip("[]")
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return None
    return candidate


async def _resolve_host_ips(host: str) -> list[str]:
    """Resolve *host* to a de-duplicated list of IP address strings."""
    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo,
            host,
            None,
            type=socket.SOCK_STREAM,
        )
    except OSError:
        return []

    addresses: list[str] = []
    for info in infos:
        addr = str(info[4][0])
        if addr not in addresses:
            addresses.append(addr)
    return addresses


def _ip_is_blocked(ip_str: str) -> bool:
    """Return True when *ip_str* is a non-public destination."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        # Unparseable addresses are never considered safe.
        return True

    # Unwrap IPv4-mapped IPv6 addresses (e.g. ``::ffff:127.0.0.1``) so a
    # private IPv4 literal smuggled through IPv6 notation is still blocked.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped

    return (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_private
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


__all__ = [
    "MAX_REDIRECTS",
    "SSRFValidationError",
    "validate_rss_http_url",
]
