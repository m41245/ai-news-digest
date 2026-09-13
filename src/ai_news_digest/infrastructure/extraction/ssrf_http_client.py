from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from http import HTTPStatus
from typing import TYPE_CHECKING

import httpx

from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.extraction_method import ExtractionMethod
from ai_news_digest.domain.enums.extraction_quality import ExtractionQuality
from ai_news_digest.infrastructure.rss.url_safety import (
    MAX_REDIRECTS,
    SSRFValidationError,
    validate_rss_http_url,
)

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

_USER_AGENT = "ai-news-digest/0.1 (+Article fetcher)"
_ACCEPT = "text/html,application/xhtml+xml,text/plain,text/*,application/xml;q=0.9,*/*;q=0.1"
_CHUNK_SIZE = 64 * 1024


class ArticleFetchError(Exception):
    """Raised when an article cannot be fetched."""


@dataclass(slots=True)
class FetchResult:
    content: str
    method: ExtractionMethod = ExtractionMethod.HTML
    quality: ExtractionQuality = ExtractionQuality.HIGH
    extracted_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    failure_reason: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    redirected: bool = False


class SsrfHttpArticleFetcher:
    def __init__(
        self,
        *,
        timeout: float = 20.0,
        max_response_bytes: int = 5_000_000,
        max_redirects: int = MAX_REDIRECTS,
        user_agent: str = _USER_AGENT,
    ) -> None:
        self._timeout = timeout
        self._max_response_bytes = max_response_bytes
        self._max_redirects = max_redirects
        self._user_agent = user_agent

    async def fetch(self, url: str) -> FetchResult:
        logger.info("Fetching article", url=url)

        try:
            validated_url = await validate_rss_http_url(url)
        except SSRFValidationError as exc:
            logger.warning(
                "Article URL rejected by SSRF validation", url=url, error=str(exc)
            )
            return FetchResult(
                content="",
                failure_reason=f"SSRF validation failed: {exc}",
            )

        headers = {
            "User-Agent": self._user_agent,
            "Accept": _ACCEPT,
        }
        timeout = httpx.Timeout(self._timeout)
        current_url = validated_url
        redirected = False

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            headers=headers,
        ) as client:
            for _ in range(self._max_redirects + 1):
                try:
                    response = await client.get(current_url)
                except httpx.TimeoutException as exc:
                    logger.warning(
                        "Article fetch timed out",
                        url=current_url,
                        error=str(exc),
                    )
                    return FetchResult(
                        content="",
                        failure_reason=(
                            f"Timed out while fetching article '{current_url}'."
                        ),
                    )
                except httpx.HTTPError as exc:
                    logger.warning(
                        "Article fetch HTTP error",
                        url=current_url,
                        error=str(exc),
                    )
                    return FetchResult(
                        content="",
                        failure_reason=(
                            f"Failed to fetch article '{current_url}': {exc}"
                        ),
                    )

                status = response.status_code
                content_type = response.headers.get("content-type", "")

                if HTTPStatus.MULTIPLE_CHOICES <= status < HTTPStatus.BAD_REQUEST:
                    location = response.headers.get("location")
                    if not location:
                        logger.warning(
                            "Article redirect missing Location header",
                            url=current_url,
                        )
                        return FetchResult(
                            content="",
                            status_code=status,
                            failure_reason=(
                                f"Article '{current_url}' returned a redirect "
                                "without a Location header."
                            ),
                        )

                    target = str(response.url.join(location))

                    try:
                        validated_target = await validate_rss_http_url(target)
                    except SSRFValidationError as exc:
                        logger.warning(
                            "Article redirect rejected",
                            url=current_url,
                            redirect_to=target,
                            error=str(exc),
                        )
                        return FetchResult(
                            content="",
                            status_code=status,
                            failure_reason=(
                                f"Article redirect to '{target}' rejected: {exc}"
                            ),
                        )

                    redirected = True
                    current_url = validated_target
                    continue

                if status >= HTTPStatus.BAD_REQUEST:
                    logger.warning(
                        "Article fetch returned bad status",
                        url=current_url,
                        status_code=status,
                    )
                    return FetchResult(
                        content="",
                        status_code=status,
                        failure_reason=(
                            f"Article '{current_url}' returned HTTP {status}."
                        ),
                    )

                if not _is_supported_content_type(content_type):
                    logger.warning(
                        "Article fetch unsupported content type",
                        url=current_url,
                        content_type=content_type,
                    )
                    return FetchResult(
                        content="",
                        status_code=status,
                        content_type=content_type,
                        failure_reason=(
                            f"Article '{current_url}' has unsupported content "
                            f"type '{content_type}'."
                        ),
                    )

                body_bytes = await _read_body(
                    response, current_url, self._max_response_bytes
                )
                if body_bytes is None:
                    logger.warning(
                        "Article fetch body too large",
                        url=current_url,
                        max_bytes=self._max_response_bytes,
                    )
                    return FetchResult(
                        content="",
                        status_code=status,
                        content_type=content_type,
                        redirected=redirected,
                        failure_reason=(
                            f"Article '{current_url}' body exceeds the maximum "
                            f"allowed size ({self._max_response_bytes} bytes)."
                        ),
                    )

                try:
                    text = body_bytes.decode(
                        response.encoding or "utf-8", errors="replace"
                    )
                except (LookupError, UnicodeDecodeError):
                    text = body_bytes.decode("utf-8", errors="replace")

                logger.info(
                    "Article fetch success",
                    url=current_url,
                    content_size=len(text),
                )
                return FetchResult(
                    content=text,
                    status_code=status,
                    content_type=content_type,
                    redirected=redirected,
                )

            logger.warning(
                "Article fetch exceeded maximum redirects",
                url=validated_url,
                max_redirects=self._max_redirects,
            )
            return FetchResult(
                content="",
                failure_reason=(
                    f"Article '{validated_url}' exceeded the maximum number "
                    f"of redirects ({self._max_redirects})."
                ),
            )


def _is_supported_content_type(content_type: str) -> bool:
    if not content_type:
        return False

    main_type = content_type.strip().lower().split(";")[0].strip()

    blocked_prefixes = ("application/pdf", "image/")
    for prefix in blocked_prefixes:
        if main_type.startswith(prefix):
            return False

    if main_type == "text/html":
        return True
    if main_type == "application/xhtml+xml":
        return True
    if main_type == "text/plain":
        return True
    return bool(main_type.startswith("text/"))


async def _read_body(
    response: httpx.Response,
    url: str,
    max_bytes: int,
) -> bytes | None:
    content_length = response.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                return None
        except ValueError:
            pass

    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_bytes(_CHUNK_SIZE):
        total += len(chunk)
        if total > max_bytes:
            return None
        chunks.append(chunk)

    return b"".join(chunks)


__all__ = [
    "ArticleFetchError",
    "FetchResult",
    "SsrfHttpArticleFetcher",
]
