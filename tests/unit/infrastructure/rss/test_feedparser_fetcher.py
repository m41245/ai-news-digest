"""
Unit tests for FeedparserFetcher.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_news_digest.infrastructure.rss.feedparser_fetcher import (
    FeedFetchError,
    FeedparserFetcher,
)

# A dummy feed body returned by the mocked _download step.
_FAKE_BODY = b"<?xml version='1.0'?><rss><channel></channel></rss>"
_FAKE_HEADERS = {"content-type": "application/xml"}


@pytest.fixture
def fetcher() -> FeedparserFetcher:
    """Create a FeedparserFetcher instance."""
    return FeedparserFetcher()


def _download_mock(body: bytes = _FAKE_BODY):
    """Return an async function that mimics ``FeedparserFetcher._download``."""

    async def _download(url: str) -> tuple[bytes, dict[str, str]]:
        return (body, dict(_FAKE_HEADERS))

    return _download


def _make_entry(
    title: str = "Article",
    link: str = "https://example.com/article",
    summary: str = "Summary",
    content: object = None,
    published: str | None = "Mon, 01 Jan 2024 00:00:00 GMT",
    author: str | None = None,
    entry_id: str | None = None,
) -> MagicMock:
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = summary
    entry.description = ""
    entry.content = content
    entry.published = published
    entry.author = author
    entry.id = entry_id
    return entry


def _make_feed(
    entries: list[MagicMock] | None = None,
    status: int | None = None,
    bozo: bool = False,
    bozo_exception: Exception | None = None,
) -> MagicMock:
    feed = MagicMock()
    feed.entries = entries or []
    feed.status = status
    feed.bozo = bozo
    feed.bozo_exception = bozo_exception
    return feed


@pytest.mark.asyncio
async def test_feedparser_fetch_success(fetcher: FeedparserFetcher) -> None:
    """Test successful feed fetch."""
    mock_feed = _make_feed(
        entries=[
            _make_entry(
                title="Article 1",
                link="https://example.com/article1",
                content="Content 1",
            ),
            _make_entry(title="Article 2", link="https://example.com/article2"),
        ],
        status=200,
    )

    with (
        patch.object(fetcher, "_download", _download_mock()),
        patch("feedparser.parse", return_value=mock_feed),
    ):
        result = await fetcher.fetch("https://example.com/feed.xml")

        assert len(result) == 2
        assert result[0].title == "Article 1"
        assert result[0].url == "https://example.com/article1"
        assert result[0].summary == "Summary"
        assert result[0].content == "Content 1"
        assert result[1].title == "Article 2"
        assert result[1].content is None


@pytest.mark.asyncio
async def test_feedparser_fetch_empty_feed(fetcher: FeedparserFetcher) -> None:
    """Test fetch with empty feed."""
    with (
        patch.object(fetcher, "_download", _download_mock()),
        patch("feedparser.parse", return_value=_make_feed(entries=[])),
    ):
        result = await fetcher.fetch("https://example.com/feed.xml")

        assert len(result) == 0


@pytest.mark.asyncio
async def test_feedparser_fetch_missing_fields(fetcher: FeedparserFetcher) -> None:
    """Test fetch with entries missing optional fields."""
    with (
        patch.object(fetcher, "_download", _download_mock()),
        patch(
            "feedparser.parse",
            return_value=_make_feed(entries=[_make_entry(published=None)]),
        ),
    ):
        result = await fetcher.fetch("https://example.com/feed.xml")

        assert len(result) == 1
        assert result[0].title == "Article"
        assert result[0].published_at is not None


def test_parse_datetime_valid(fetcher: FeedparserFetcher) -> None:
    """Test parsing valid datetime string."""
    result = fetcher._parse_datetime("Mon, 01 Jan 2024 00:00:00 GMT")

    assert result is not None
    assert result.tzinfo is not None


def test_parse_datetime_none(fetcher: FeedparserFetcher) -> None:
    """Test parsing None datetime."""
    result = fetcher._parse_datetime(None)

    assert result is not None
    assert result.tzinfo is not None


def test_parse_datetime_empty_string(fetcher: FeedparserFetcher) -> None:
    """Test parsing empty string datetime."""
    result = fetcher._parse_datetime("")

    assert result is not None
    assert result.tzinfo is not None


def test_parse_datetime_invalid(fetcher: FeedparserFetcher) -> None:
    """Test parsing invalid datetime string."""
    result = fetcher._parse_datetime("invalid date")

    assert result is not None
    assert result.tzinfo is not None


def test_parse_datetime_without_timezone(fetcher: FeedparserFetcher) -> None:
    """Test parsing datetime without timezone."""
    result = fetcher._parse_datetime("Mon, 01 Jan 2024 00:00:00")

    assert result is not None
    assert result.tzinfo is not None


@pytest.mark.asyncio
async def test_feedparser_fetch_with_whitespace_fields(fetcher: FeedparserFetcher) -> None:
    """Test fetch with fields containing whitespace."""
    with (
        patch.object(fetcher, "_download", _download_mock()),
        patch(
            "feedparser.parse",
            return_value=_make_feed(
                entries=[
                    _make_entry(
                        title="  Article 1  ",
                        link="  https://example.com/article1  ",
                    )
                ]
            ),
        ),
    ):
        result = await fetcher.fetch("https://example.com/feed.xml")

        assert result[0].title == "Article 1"
        assert result[0].url == "https://example.com/article1"


@pytest.mark.asyncio
async def test_feedparser_fetch_http_error_raises(fetcher: FeedparserFetcher) -> None:
    """A 4xx/5xx status on the parsed feed raises FeedFetchError."""
    with (
        patch.object(fetcher, "_download", _download_mock()),
        patch("feedparser.parse", return_value=_make_feed(status=404)),
        pytest.raises(FeedFetchError, match="HTTP 404"),
    ):
        await fetcher.fetch("https://example.com/missing.xml")


@pytest.mark.asyncio
async def test_feedparser_fetch_not_modified_returns_empty(fetcher: FeedparserFetcher) -> None:
    """An empty body (304 Not Modified) yields no entries."""
    with patch.object(fetcher, "_download", _download_mock(body=b"")):
        result = await fetcher.fetch("https://example.com/feed.xml")

        assert result == []


@pytest.mark.asyncio
async def test_feedparser_fetch_bozo_irreparable_raises(fetcher: FeedparserFetcher) -> None:
    """A feed with a non-recoverable parse error raises FeedFetchError."""
    with (
        patch.object(fetcher, "_download", _download_mock()),
        patch(
            "feedparser.parse",
            return_value=_make_feed(
                bozo=True,
                bozo_exception=Exception("not well-formed (invalid token)"),
            ),
        ),
        pytest.raises(FeedFetchError, match="not a valid feed"),
    ):
        await fetcher.fetch("https://example.com/bad.xml")


@pytest.mark.asyncio
async def test_feedparser_fetch_bozo_recoverable_ok(fetcher: FeedparserFetcher) -> None:
    """Recoverable encoding issues do not abort parsing."""
    with (
        patch.object(fetcher, "_download", _download_mock()),
        patch(
            "feedparser.parse",
            return_value=_make_feed(
                entries=[_make_entry()],
                bozo=True,
                bozo_exception=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte"),
            ),
        ),
    ):
        result = await fetcher.fetch("https://example.com/feed.xml")

        assert len(result) == 1


@pytest.mark.asyncio
async def test_feedparser_fetch_timeout(fetcher: FeedparserFetcher) -> None:
    """A parse that exceeds the timeout raises FeedFetchError."""

    def slow_parse(*_args: object, **_kwargs: object) -> MagicMock:
        import time

        time.sleep(5)
        return _make_feed()

    fetcher_short = FeedparserFetcher(timeout=0.1)

    with (
        patch.object(fetcher_short, "_download", _download_mock()),
        patch("feedparser.parse", side_effect=slow_parse),
        pytest.raises(FeedFetchError, match="Timed out"),
    ):
        await fetcher_short.fetch("https://example.com/slow.xml")


@pytest.mark.asyncio
async def test_feedparser_fetch_malformed_entry_skipped(fetcher: FeedparserFetcher) -> None:
    """Individual malformed entries are skipped rather than aborting the feed."""
    bad_entry = MagicMock()
    bad_entry.title = None
    bad_entry.link = None
    # Remove any non-default attribute so getattr returns the default.
    del bad_entry.link

    good_entry = _make_entry(link="https://example.com/good")

    with (
        patch.object(fetcher, "_download", _download_mock()),
        patch(
            "feedparser.parse",
            return_value=_make_feed(entries=[bad_entry, good_entry]),
        ),
    ):
        result = await fetcher.fetch("https://example.com/feed.xml")

        assert len(result) == 1
        assert result[0].url == "https://example.com/good"


@pytest.mark.asyncio
async def test_feedparser_fetch_no_url_entry_skipped(fetcher: FeedparserFetcher) -> None:
    """Entries that normalize to an empty URL are dropped."""
    with (
        patch.object(fetcher, "_download", _download_mock()),
        patch(
            "feedparser.parse",
            return_value=_make_feed(entries=[_make_entry(link="   ")]),
        ),
    ):
        result = await fetcher.fetch("https://example.com/feed.xml")

        assert len(result) == 0


@pytest.mark.asyncio
async def test_feedparser_fetch_respects_max_articles() -> None:
    """The max_articles cap limits returned entries."""
    entries = [_make_entry(link=f"https://example.com/a{i}") for i in range(5)]
    fetcher_capped = FeedparserFetcher(max_articles=3)

    with (
        patch.object(fetcher_capped, "_download", _download_mock()),
        patch(
            "feedparser.parse",
            return_value=_make_feed(entries=entries),
        ),
    ):
        result = await fetcher_capped.fetch("https://example.com/feed.xml")

        assert len(result) == 3


def test_rss_entry_includes_author_and_guid() -> None:
    """Normalization captures author and guid when available."""
    fetcher = FeedparserFetcher()
    entry = _make_entry(
        author="Jane Doe",
        entry_id="unique-guid-123",
    )

    result = fetcher._normalize_entry(entry)

    assert result.author == "Jane Doe"
    assert result.guid == "unique-guid-123"
