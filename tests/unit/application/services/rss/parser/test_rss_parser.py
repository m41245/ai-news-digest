"""
Unit tests for RSSParser.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.services.rss.parser.exceptions import (
    RSSArticleValidationError,
    RSSFeedFormatError,
    RSSParsingError,
)
from ai_news_digest.application.services.rss.parser.rss_parser import RSSParser


@pytest.fixture
def parser() -> RSSParser:
    """Create an RSSParser instance."""
    return RSSParser()


# RSS Feed Tests


def test_parse_valid_rss_feed(parser: RSSParser) -> None:
    """Test parsing a valid RSS 2.0 feed."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article 1</title>
      <link>https://example.com/article1</link>
      <description>Summary 1</description>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""

    articles = parser.parse(xml)

    assert len(articles) == 1
    assert articles[0].title == "Article 1"
    assert articles[0].url == "https://example.com/article1"
    assert articles[0].summary == "Summary 1"


def test_parse_rss_feed_multiple_items(parser: RSSParser) -> None:
    """Test parsing RSS feed with multiple items."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article 1</title>
      <link>https://example.com/article1</link>
      <description>Summary 1</description>
    </item>
    <item>
      <title>Article 2</title>
      <link>https://example.com/article2</link>
      <description>Summary 2</description>
    </item>
  </channel>
</rss>"""

    articles = parser.parse(xml)

    assert len(articles) == 2
    assert articles[0].title == "Article 1"
    assert articles[1].title == "Article 2"


def test_parse_rss_feed_empty_description(parser: RSSParser) -> None:
    """Test parsing RSS feed with empty description."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article 1</title>
      <link>https://example.com/article1</link>
    </item>
  </channel>
</rss>"""

    articles = parser.parse(xml)

    assert len(articles) == 1
    assert articles[0].summary == ""


def test_parse_rss_feed_missing_pub_date(parser: RSSParser) -> None:
    """Test parsing RSS feed without pubDate."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article 1</title>
      <link>https://example.com/article1</link>
      <description>Summary 1</description>
    </item>
  </channel>
</rss>"""

    articles = parser.parse(xml)

    assert len(articles) == 1
    assert articles[0].published_at is not None


def test_parse_invalid_xml(parser: RSSParser) -> None:
    """Test parsing invalid XML raises RSSParsingError."""
    xml = "not valid xml"

    with pytest.raises(RSSParsingError, match="Invalid XML document"):
        parser.parse(xml)


def test_parse_rss_missing_channel(parser: RSSParser) -> None:
    """Test parsing RSS feed without channel raises RSSFeedFormatError."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
</rss>"""

    with pytest.raises(RSSFeedFormatError, match="RSS channel not found"):
        parser.parse(xml)


def test_parse_rss_missing_title(parser: RSSParser) -> None:
    """Test parsing RSS item without title raises RSSArticleValidationError."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <link>https://example.com/article1</link>
      <description> Summary 1</description>
    </item>
  </channel>
</rss>"""

    with pytest.raises(RSSArticleValidationError, match="Missing required field: title"):
        parser.parse(xml)


def test_parse_rss_missing_link(parser: RSSParser) -> None:
    """Test parsing RSS item without link raises RSSArticleValidationError."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article 1</title>
      <description>Summary 1</description>
    </item>
  </channel>
</rss>"""

    with pytest.raises(RSSArticleValidationError, match="Missing required field: link"):
        parser.parse(xml)


def test_parse_unsupported_feed_format(parser: RSSParser) -> None:
    """Test parsing unsupported feed format raises RSSFeedFormatError."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<unknown>
  <item>
    <title>Article 1</title>
  </item>
</unknown>"""

    with pytest.raises(RSSFeedFormatError, match="Unsupported feed format"):
        parser.parse(xml)


# Atom Feed Tests


def test_parse_valid_atom_feed(parser: RSSParser) -> None:
    """Test parsing a valid Atom feed."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Feed</title>
  <entry>
    <title>Article 1</title>
    <link href="https://example.com/article1"/>
    <summary>Summary 1</summary>
    <updated>2024-01-01T00:00:00Z</updated>
  </entry>
</feed>"""

    articles = parser.parse(xml)

    assert len(articles) == 1
    assert articles[0].title == "Article 1"
    assert articles[0].url == "https://example.com/article1"
    assert articles[0].summary == "Summary 1"


def test_parse_atom_feed_multiple_entries(parser: RSSParser) -> None:
    """Test parsing Atom feed with multiple entries."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Feed</title>
  <entry>
    <title>Article 1</title>
    <link href="https://example.com/article1"/>
    <summary>Summary 1</summary>
  </entry>
  <entry>
    <title>Article 2</title>
    <link href="https://example.com/article2"/>
    <summary>Summary 2</summary>
  </entry>
</feed>"""

    articles = parser.parse(xml)

    assert len(articles) == 2
    assert articles[0].title == "Article 1"
    assert articles[1].title == "Article 2"


def test_parse_atom_feed_empty_summary(parser: RSSParser) -> None:
    """Test parsing Atom feed with empty summary."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Feed</title>
  <entry>
    <title>Article 1</title>
    <link href="https://example.com/article1"/>
  </entry>
</feed>"""

    articles = parser.parse(xml)

    assert len(articles) == 1
    assert articles[0].summary == ""


def test_parse_atom_feed_missing_link(parser: RSSParser) -> None:
    """Test parsing Atom entry without link raises RSSArticleValidationError."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Feed</title>
  <entry>
    <title>Article 1</title>
    <summary>Summary 1</summary>
  </entry>
</feed>"""

    with pytest.raises(RSSArticleValidationError, match="Atom entry missing link"):
        parser.parse(xml)


def test_parse_atom_feed_missing_link_href(parser: RSSParser) -> None:
    """Test parsing Atom entry with link without href raises RSSArticleValidationError."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Feed</title>
  <entry>
    <title>Article 1</title>
    <link rel="alternate"/>
    <summary>Summary 1</summary>
  </entry>
</feed>"""

    with pytest.raises(RSSArticleValidationError, match="Atom entry missing link"):
        parser.parse(xml)


def test_parse_atom_feed_missing_title(parser: RSSParser) -> None:
    """Test parsing Atom entry without title raises RSSArticleValidationError."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Feed</title>
  <entry>
    <link href="https://example.com/article1"/>
    <summary>Summary 1</summary>
  </entry>
</feed>"""

    with pytest.raises(RSSArticleValidationError, match="Missing required field: title"):
        parser.parse(xml)


# Date Parsing Tests


def test_parse_date_valid(parser: RSSParser) -> None:
    """Test parsing valid date string."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article 1</title>
      <link>https://example.com/article1</link>
      <description>Summary 1</description>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""

    articles = parser.parse(xml)

    assert articles[0].published_at is not None
    assert articles[0].published_at.tzinfo is not None


def test_parse_date_invalid(parser: RSSParser) -> None:
    """Test parsing invalid date string falls back to current time."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article 1</title>
      <link>https://example.com/article1</link>
      <description>Summary 1</description>
      <pubDate>invalid date</pubDate>
    </item>
  </channel>
</rss>"""

    articles = parser.parse(xml)

    assert articles[0].published_at is not None


def test_parse_date_none(parser: RSSParser) -> None:
    """Test parsing None date falls back to current time."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article 1</title>
      <link>https://example.com/article1</link>
      <description>Summary 1</description>
    </item>
  </channel>
</rss>"""

    articles = parser.parse(xml)

    assert articles[0].published_at is not None


def test_parse_atom_date_with_updated(parser: RSSParser) -> None:
    """Test parsing Atom entry with updated date."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Feed</title>
  <entry>
    <title>Article 1</title>
    <link href="https://example.com/article1"/>
    <updated>2024-01-01T00:00:00Z</updated>
  </entry>
</feed>"""

    articles = parser.parse(xml)

    assert articles[0].published_at is not None


def test_parse_atom_date_with_published(parser: RSSParser) -> None:
    """Test parsing Atom entry with published date."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Feed</title>
  <entry>
    <title>Article 1</title>
    <link href="https://example.com/article1"/>
    <published>2024-01-01T00:00:00Z</published>
  </entry>
</feed>"""

    articles = parser.parse(xml)

    assert articles[0].published_at is not None


# Namespace Tests


def test_parse_rss_with_namespace(parser: RSSParser) -> None:
    """Test parsing RSS feed with namespace."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article 1</title>
      <link>https://example.com/article1</link>
      <description>Summary 1</description>
    </item>
  </channel>
</rss>"""

    articles = parser.parse(xml)

    assert len(articles) == 1
    assert articles[0].title == "Article 1"


def test_parse_atom_with_custom_namespace(parser: RSSParser) -> None:
    """Test parsing Atom feed with custom namespace."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:custom="http://example.com/ns">
  <title>Test Feed</title>
  <entry>
    <title>Article 1</title>
    <link href="https://example.com/article1"/>
    <custom:field>value</custom:field>
  </entry>
</feed>"""

    articles = parser.parse(xml)

    assert len(articles) == 1
    assert articles[0].title == "Article 1"
