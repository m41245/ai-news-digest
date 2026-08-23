"""
Unit tests for DigestBuilder.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_news_digest.application.digest.digest_builder import DigestBuilder
from ai_news_digest.application.dto.digest_article_view import DigestArticleView


@pytest.fixture
def builder() -> DigestBuilder:
    return DigestBuilder()


@pytest.fixture
def sample_views() -> list[DigestArticleView]:
    return [
        DigestArticleView(
            article_id=uuid4(),
            title="Article 1",
            url="https://example.com/article1",
            summary="Summary 1",
            source_name="Source A",
            category_name="AI",
            published_at=datetime(2024, 1, 3, 12, 0, 0, tzinfo=UTC),
        ),
        DigestArticleView(
            article_id=uuid4(),
            title="Article 2",
            url="https://example.com/article2",
            summary="Summary 2",
            source_name="Source B",
            category_name="Tech",
            published_at=datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC),
        ),
        DigestArticleView(
            article_id=uuid4(),
            title="Article 3",
            url="https://example.com/article3",
            summary="Summary 3",
            source_name="Source A",
            category_name=None,
            published_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        ),
    ]


def test_digest_builder_build_empty(builder: DigestBuilder) -> None:
    """Test building digest with no articles."""
    result = builder.build(
        title="Empty Digest",
        generated_at=datetime.now(UTC),
        articles=[],
    )

    assert "# Empty Digest" in result
    assert "*No articles in this digest.*" in result


def test_digest_builder_build_with_articles(
    builder: DigestBuilder, sample_views: list[DigestArticleView]
) -> None:
    """Test building digest with articles."""
    result = builder.build(
        title="Test Digest",
        generated_at=datetime(2024, 1, 3, 8, 0, 0, tzinfo=UTC),
        articles=sample_views,
    )

    assert "# Test Digest" in result
    assert "**Generated:** 2024-01-03 08:00 UTC" in result
    assert "---" in result
    assert "Article 1" in result
    assert "Article 2" in result
    assert "Article 3" in result
    assert "Source A" in result
    assert "Source B" in result
    assert "https://example.com/article1" in result
    assert "[Read article](https://example.com/article1)" in result
    assert "Summary 1" in result


def test_digest_builder_groups_by_category(
    builder: DigestBuilder, sample_views: list[DigestArticleView]
) -> None:
    """Test that articles are grouped by category."""
    result = builder.build(
        title="Test Digest",
        generated_at=datetime.now(UTC),
        articles=sample_views,
    )

    assert "## AI" in result
    assert "## Tech" in result
    assert "## Uncategorized" in result


def test_digest_builder_sorts_categories(
    builder: DigestBuilder, sample_views: list[DigestArticleView]
) -> None:
    """Test that categories are sorted alphabetically."""
    result = builder.build(
        title="Test Digest",
        generated_at=datetime.now(UTC),
        articles=sample_views,
    )

    ai_index = result.index("## AI")
    tech_index = result.index("## Tech")
    uncategorized_index = result.index("## Uncategorized")

    assert ai_index < tech_index < uncategorized_index


def test_digest_builder_sorts_articles_within_category(
    builder: DigestBuilder, sample_views: list[DigestArticleView]
) -> None:
    """Test that articles within a category are sorted by published_at desc."""
    result = builder.build(
        title="Test Digest",
        generated_at=datetime.now(UTC),
        articles=sample_views,
    )

    tech_pos = result.index("## Tech")
    article2_pos = result.index("Article 2")
    assert article2_pos > tech_pos


def test_digest_builder_deterministic_output(
    builder: DigestBuilder, sample_views: list[DigestArticleView]
) -> None:
    """Test that builder produces deterministic output."""
    result1 = builder.build(
        title="Test Digest",
        generated_at=datetime(2024, 1, 3, 8, 0, 0, tzinfo=UTC),
        articles=sample_views,
    )
    result2 = builder.build(
        title="Test Digest",
        generated_at=datetime(2024, 1, 3, 8, 0, 0, tzinfo=UTC),
        articles=sample_views,
    )

    assert result1 == result2


def test_digest_builder_handles_special_characters(builder: DigestBuilder) -> None:
    """Test that builder handles special characters in article data."""
    views = [
        DigestArticleView(
            article_id=uuid4(),
            title="Article <with> & special 'chars'",
            url="https://example.com/article?utm_source=test",
            summary="Summary with *markdown* chars",
            source_name="Source & Co",
            category_name="AI/ML",
            published_at=datetime.now(UTC),
        ),
    ]

    result = builder.build(
        title="Test Digest",
        generated_at=datetime.now(UTC),
        articles=views,
    )

    assert "Article <with> & special 'chars'" in result
    assert "Source & Co" in result
    assert "Summary with *markdown* chars" in result
