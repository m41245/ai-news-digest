from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from types import TracebackType

import httpx

from .constants import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_USER_AGENT,
)
from .exceptions import (
    RSSConnectionError,
    RSSInvalidResponseError,
    RSSRequestError,
    RSSTimeoutError,
)

logger = logging.getLogger(__name__)


class RSSClient:
    """
    Asynchronous HTTP client responsible for downloading RSS/Atom feeds.

    Responsibilities:
        - Download RSS/Atom XML
        - Retry transient failures
        - Handle timeouts
        - Raise typed exceptions

    This class intentionally performs no XML parsing.
    """

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._user_agent = user_agent

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            headers={
                "User-Agent": user_agent,
                "Accept": ("application/rss+xml,application/atom+xml,application/xml,text/xml"),
            },
        )

    async def __aenter__(self) -> RSSClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def fetch(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        """
        Download an RSS/Atom feed and return the raw XML.
        """
        request_headers: dict[str, str] = {}

        if headers is not None:
            request_headers.update(headers)

        last_exception: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                logger.debug(
                    "Fetching RSS feed '%s' (attempt %d/%d)",
                    url,
                    attempt,
                    self._max_retries,
                )

                response = await self._client.get(
                    url,
                    headers=request_headers,
                )

                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "").lower()

                self._validate_content_type(content_type)

                logger.info(
                    "Successfully fetched RSS feed '%s'",
                    url,
                )

                return response.text

            except httpx.TimeoutException as exc:
                last_exception = exc

                logger.warning(
                    "RSS request timed out: %s",
                    url,
                )

            except httpx.ConnectError as exc:
                last_exception = exc

                logger.warning(
                    "Unable to connect to RSS feed: %s",
                    url,
                )

            except httpx.HTTPStatusError as exc:
                raise RSSRequestError(
                    f"HTTP {exc.response.status_code} while requesting '{url}'."
                ) from exc

            except httpx.HTTPError as exc:
                raise RSSRequestError(f"Unexpected HTTP error while requesting '{url}'.") from exc

            if attempt < self._max_retries:
                delay = self._backoff_factor * (2 ** (attempt - 1))

                logger.debug(
                    "Retrying '%s' in %.1f seconds...",
                    url,
                    delay,
                )

                await asyncio.sleep(delay)

        if isinstance(last_exception, httpx.TimeoutException):
            raise RSSTimeoutError(f"Timed out while requesting '{url}'.") from last_exception

        if isinstance(last_exception, httpx.ConnectError):
            raise RSSConnectionError(f"Unable to connect to '{url}'.") from last_exception

        raise RSSRequestError(f"Failed to fetch '{url}'.") from last_exception

    @staticmethod
    def _validate_content_type(
        content_type: str,
    ) -> None:
        """
        Validate that the server returned XML.

        Raises:
            RSSInvalidResponseError:
                If the response does not appear to contain
                RSS or Atom XML.
        """

        valid_types = (
            "application/rss+xml",
            "application/atom+xml",
            "application/xml",
            "text/xml",
            "application/xhtml+xml",
            "text/plain",
        )

        if any(media_type in content_type for media_type in valid_types):
            return

        raise RSSInvalidResponseError(
            f"Server returned an unexpected Content-Type: '{content_type}'."
        )
