from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from http import HTTPStatus

import feedparser
from feedparser import FeedParserDict

from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.models.rss_entry import RssEntry
from ai_news_digest.domain.ports.rss_fetcher import RSSFetcher

logger = get_logger(__name__)


class FeedFetchError(Exception):
    """Raised when a feed cannot be retrieved or parsed."""


class FeedparserFetcher(RSSFetcher):
    """
    RSSFetcher implementation backed by feedparser.

    ``feedparser.parse`` performs blocking HTTP I/O, so the actual fetch runs
    in a thread pool via :func:`asyncio.to_thread` to avoid blocking the event
    loop. A configurable timeout bounds the operation.
    """

    def __init__(
        self,
        *,
        timeout: float = 20.0,
        max_articles: int = 50,
    ) -> None:
        self._timeout = timeout
        self._max_articles = max_articles

    async def fetch(
        self,
        feed_url: str,
    ) -> list[RssEntry]:
        """Fetch and normalize a single RSS feed."""

        try:
            feed = await asyncio.wait_for(
                asyncio.to_thread(feedparser.parse, feed_url),
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            raise FeedFetchError(f"Timed out while fetching feed '{feed_url}'.") from exc
        except Exception as exc:
            raise FeedFetchError(f"Failed to fetch feed '{feed_url}': {exc}") from exc

        return self._parse(feed, feed_url)

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
