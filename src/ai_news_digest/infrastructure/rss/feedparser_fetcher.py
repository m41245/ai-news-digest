from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from http import HTTPStatus

import feedparser
import httpx
from feedparser import FeedParserDict

from ai_news_digest.core.config import settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.models.rss_entry import RssEntry
from ai_news_digest.domain.ports.rss_fetcher import RSSFetcher
from ai_news_digest.infrastructure.rss.url_safety import (
    MAX_REDIRECTS,
    SSRFValidationError,
    validate_rss_http_url,
)

logger = get_logger(__name__)

_USER_AGENT = "ai-news-digest/0.1 (+RSS feed fetcher)"
_ACCEPT = "application/rss+xml,application/atom+xml,application/xml,text/xml;q=0.9,*/*;q=0.1"
_CHUNK_SIZE = 64 * 1024


class FeedFetchError(Exception):
    """Raised when a feed cannot be retrieved or parsed."""


class FeedparserFetcher(RSSFetcher):
    """
    RSSFetcher implementation backed by feedparser.

    The HTTP fetch is performed through an SSRF-safe boundary
    (:mod:`ai_news_digest.infrastructure.rss.url_safety`): only public
    http(s) destinations are reachable, redirects are re-validated on every
    hop, the response body is capped, and a configurable timeout bounds the
    operation. The downloaded payload is passed to ``feedparser.parse`` (a
    CPU-bound, blocking call) inside a thread pool via :func:`asyncio.to_thread`
    so the event loop is never blocked.
    """

    def __init__(
        self,
        *,
        timeout: float = 20.0,
        max_articles: int = 50,
        max_redirects: int = MAX_REDIRECTS,
        max_response_bytes: int = settings.rss_max_response_bytes,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout = timeout
        self._max_articles = max_articles
        self._max_redirects = max_redirects
        self._max_response_bytes = max_response_bytes
        self._transport = transport

    async def fetch(
        self,
        feed_url: str,
    ) -> list[RssEntry]:
        """Fetch and normalize a single RSS feed."""

        try:
            url = await validate_rss_http_url(feed_url)
        except SSRFValidationError as exc:
            raise FeedFetchError(f"Feed URL rejected: {exc}") from exc

        data, headers = await self._download(url)

        if data == b"":
            return []

        feed = await self._parse_payload(data, headers, url)

        return self._parse(feed, url)

    async def _download(self, url: str) -> tuple[bytes, dict[str, str]]:
        """
        Download the feed body over an SSRF-safe HTTP boundary.

        Returns ``(body_bytes, response_headers)``. An empty body is returned
        for ``304 Not Modified`` responses.
        """
        timeout = httpx.Timeout(self._timeout)
        headers = {"User-Agent": _USER_AGENT, "Accept": _ACCEPT}

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            headers=headers,
            transport=self._transport,
        ) as client:
            current_url = url

            for _ in range(self._max_redirects + 1):
                try:
                    response = await client.get(current_url)
                except httpx.TimeoutException as exc:
                    raise FeedFetchError(f"Timed out while fetching feed '{url}'.") from exc
                except httpx.HTTPError as exc:
                    raise FeedFetchError(f"Failed to fetch feed '{url}': {exc}") from exc

                status = response.status_code

                if status == HTTPStatus.NOT_MODIFIED:
                    return b"", {}

                if status >= HTTPStatus.BAD_REQUEST:
                    raise FeedFetchError(f"Feed '{url}' returned HTTP {status}.")

                if HTTPStatus.MULTIPLE_CHOICES <= status < HTTPStatus.BAD_REQUEST:
                    location = response.headers.get("location")
                    if not location:
                        raise FeedFetchError(
                            f"Feed '{url}' returned a redirect without a Location header."
                        )
                    target = str(response.url.join(location))
                    try:
                        current_url = await validate_rss_http_url(target)
                    except SSRFValidationError as exc:
                        raise FeedFetchError(f"Feed redirect rejected: {exc}") from exc
                    continue

                return await self._read_body(response, url)

        raise FeedFetchError(f"Feed '{url}' exceeded the maximum number of redirects.")

    async def _read_body(
        self,
        response: httpx.Response,
        url: str,
    ) -> tuple[bytes, dict[str, str]]:
        """Read the response body, enforcing the configured size cap."""
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self._max_response_bytes:
                    raise FeedFetchError(
                        f"Feed '{url}' body exceeds the maximum allowed size "
                        f"({self._max_response_bytes} bytes)."
                    )
            except ValueError:
                # Non-numeric Content-Length: fall through to streamed cap.
                pass

        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes(_CHUNK_SIZE):
            total += len(chunk)
            if total > self._max_response_bytes:
                raise FeedFetchError(
                    f"Feed '{url}' body exceeds the maximum allowed size "
                    f"({self._max_response_bytes} bytes)."
                )
            chunks.append(chunk)

        return b"".join(chunks), dict(response.headers)

    async def _parse_payload(
        self,
        data: bytes,
        headers: dict[str, str],
        feed_url: str,
    ) -> FeedParserDict:
        """Parse a downloaded feed payload with feedparser off the event loop."""
        response_headers = {"content-type": headers.get("content-type", "")}
        try:
            feed = await asyncio.wait_for(
                asyncio.to_thread(
                    feedparser.parse,
                    data,
                    response_headers=response_headers,
                ),
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            raise FeedFetchError(f"Timed out while parsing feed '{feed_url}'.") from exc
        except Exception as exc:
            raise FeedFetchError(f"Failed to fetch feed '{feed_url}': {exc}") from exc

        return feed

    def _parse(
        self,
        feed: FeedParserDict,
        feed_url: str,
    ) -> list[RssEntry]:
        """
        Normalize a parsed feed into RssEntry objects.

        Raises FeedFetchError for HTTP errors and for feeds whose parse was
        interrupted by a non-recoverable error. Missing or unparseable
        individual entries degrade gracefully.
        """

        status = getattr(feed, "status", None)

        if status is not None:
            if status >= HTTPStatus.BAD_REQUEST:
                raise FeedFetchError(f"Feed '{feed_url}' returned HTTP {status}.")

            if status == HTTPStatus.NOT_MODIFIED:
                return []

        if getattr(feed, "bozo", False):
            exception = getattr(feed, "bozo_exception", None)

            if exception is not None and not _is_recoverable_bozo(exception):
                raise FeedFetchError(
                    f"Feed '{feed_url}' is not a valid feed: {exception}"
                ) from exception

        raw_entries = getattr(feed, "entries", None) or []

        entries: list[RssEntry] = []

        for item in raw_entries[: self._max_articles]:
            try:
                entry = self._normalize_entry(item)
            except Exception:
                logger.debug("Skipping malformed feed entry.")
                continue

            if not entry.url:
                continue

            entries.append(entry)

        return entries

    def _normalize_entry(
        self,
        item: object,
    ) -> RssEntry:
        title = _text(getattr(item, "title", "")) or ""
        url = _text(getattr(item, "link", "")) or ""
        summary = (
            _text(getattr(item, "summary", "")) or _text(getattr(item, "description", "")) or ""
        )
        content = _text(getattr(item, "content", None))
        author = _text(getattr(item, "author", None))
        guid = _text(getattr(item, "id", None))

        published_at = self._parse_datetime(getattr(item, "published", None))

        return RssEntry(
            title=title,
            url=url,
            summary=summary,
            content=content,
            published_at=published_at,
            author=author,
            guid=guid,
        )

    @staticmethod
    def _parse_datetime(
        value: str | None,
    ) -> datetime:
        """Convert an RSS datetime string into UTC."""

        if not value:
            return datetime.now(UTC)

        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return datetime.now(UTC)

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)

        return parsed.astimezone(UTC)


def _text(value: object) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        return value.strip() or None

    return str(value).strip() or None


def _is_recoverable_bozo(exception: BaseException) -> bool:
    """
    feedparser sets ``bozo=1`` for both fatal XML well-formedness errors and
    recoverable encoding quirks. Encoding issues are recoverable; well-formedness
    errors are not.
    """

    recoverable_types = (
        UnicodeDecodeError,
        UnicodeEncodeError,
        LookupError,
    )

    if isinstance(exception, recoverable_types):
        return True

    name = type(exception).__name__
    return "Encoding" in name or "charset" in str(exception).lower()
