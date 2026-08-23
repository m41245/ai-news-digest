"""
Unit tests for GenerateDigestUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ai_news_digest.application.use_cases.digest.generate_digest import (
    GenerateDigestUseCase,
)
from ai_news_digest.core.exceptions import ValidationError
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.domain.models.source import Source


@pytest.fixture
def sample_articles() -> list[Article]:
    """Create sample articles for testing."""
    return [
        Article.create(
            title="Article 1",
            url="https://example.com/article1",
            summary="Summary 1",
            content="Content 1",
            source_id=uuid4(),
            published_at=datetime(2024, 1, 3, 12, 0, 0, tzinfo=UTC),
        ),
        Article.create(
            title="Article 2",
            url="https://example.com/article2",
            summary="Summary 2",
            content="Content 2",
            source_id=uuid4(),
            published_at=datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC),
        ),
        Article.create(
            title="Article 3",
            url="https://example.com/article3",
            summary="Summary 3",
            content="Content 3",
            source_id=uuid4(),
            published_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        ),
    ]


async def test_generate_digest_success(
    sample_articles: list[Article],
    mock_article_repository: AsyncMock,
    mock_digest_repository: AsyncMock,
    mock_source_repository: AsyncMock,
    mock_category_repository: AsyncMock,
) -> None:
    """Test successful digest generation with explicit content."""
    mock_article_repository.list_digest_eligible.return_value = sample_articles
    mock_source_repository.list_all.return_value = []
    mock_category_repository.list_all.return_value = []

    digest_id = uuid4()
    digest = Digest.create(
        title="Test Digest",
        content="Digest content",
        digest_format=DigestFormat.MARKDOWN,
        article_ids=[article.id for article in sample_articles],
    )
    object.__setattr__(digest, "id", digest_id)

    mock_digest_repository.create.return_value = digest

    use_case = GenerateDigestUseCase(
        article_repository=mock_article_repository,
        digest_repository=mock_digest_repository,
        source_repository=mock_source_repository,
        category_repository=mock_category_repository,
    )

    result = await use_case.execute(
        title="Test Digest",
        content="Digest content",
    )

    assert result.digest_id == digest_id
    assert result.included_articles == 3
    assert isinstance(result.generated_at, datetime)
    mock_article_repository.list_digest_eligible.assert_called_once_with(limit=None)
    mock_digest_repository.create.assert_called_once()


async def test_generate_digest_with_limit(
    sample_articles: list[Article],
    mock_article_repository: AsyncMock,
    mock_digest_repository: AsyncMock,
    mock_source_repository: AsyncMock,
    mock_category_repository: AsyncMock,
) -> None:
    """Test digest generation with article limit."""
    mock_article_repository.list_digest_eligible.return_value = sample_articles[:2]
    mock_source_repository.list_all.return_value = []
    mock_category_repository.list_all.return_value = []

    digest_id = uuid4()
    digest = Digest.create(
        title="Test Digest",
        content="Digest content",
        digest_format=DigestFormat.MARKDOWN,
        article_ids=[article.id for article in sample_articles[:2]],
    )
    object.__setattr__(digest, "id", digest_id)

    mock_digest_repository.create.return_value = digest

    use_case = GenerateDigestUseCase(
        article_repository=mock_article_repository,
        digest_repository=mock_digest_repository,
        source_repository=mock_source_repository,
        category_repository=mock_category_repository,
    )

    result = await use_case.execute(
        title="Test Digest",
        content="Digest content",
        limit=2,
    )

    assert result.included_articles == 2
    mock_article_repository.list_digest_eligible.assert_called_once_with(limit=2)


async def test_generate_digest_no_eligible_articles(
    mock_article_repository: AsyncMock,
    mock_digest_repository: AsyncMock,
    mock_source_repository: AsyncMock,
    mock_category_repository: AsyncMock,
) -> None:
    """Test digest generation fails when no eligible articles exist."""
    mock_article_repository.list_digest_eligible.return_value = []

    use_case = GenerateDigestUseCase(
        article_repository=mock_article_repository,
        digest_repository=mock_digest_repository,
        source_repository=mock_source_repository,
        category_repository=mock_category_repository,
    )

    with pytest.raises(ValidationError, match="No digest-eligible articles were found"):
        await use_case.execute(
            title="Test Digest",
            content="Digest content",
        )

    mock_digest_repository.create.assert_not_called()


async def test_generate_digest_sorts_by_published_at(
    sample_articles: list[Article],
    mock_article_repository: AsyncMock,
    mock_digest_repository: AsyncMock,
    mock_source_repository: AsyncMock,
    mock_category_repository: AsyncMock,
) -> None:
    """Test that articles are sorted by published_at in descending order."""
    mock_article_repository.list_digest_eligible.return_value = sample_articles
    mock_source_repository.list_all.return_value = []
    mock_category_repository.list_all.return_value = []

    digest_id = uuid4()
    digest = Digest.create(
        title="Test Digest",
        content="Digest content",
        digest_format=DigestFormat.MARKDOWN,
        article_ids=[article.id for article in sample_articles],
    )
    object.__setattr__(digest, "id", digest_id)

    mock_digest_repository.create.return_value = digest

    use_case = GenerateDigestUseCase(
        article_repository=mock_article_repository,
        digest_repository=mock_digest_repository,
        source_repository=mock_source_repository,
        category_repository=mock_category_repository,
    )

    await use_case.execute(
        title="Test Digest",
        content="Digest content",
    )

    call_args = mock_digest_repository.create.call_args
    created_digest = call_args[0][0]

    assert created_digest.article_ids[0] == sample_articles[0].id
    assert created_digest.article_ids[1] == sample_articles[1].id
    assert created_digest.article_ids[2] == sample_articles[2].id


async def test_generate_digest_auto_builds_content(
    sample_articles: list[Article],
    mock_article_repository: AsyncMock,
    mock_digest_repository: AsyncMock,
    mock_source_repository: AsyncMock,
    mock_category_repository: AsyncMock,
) -> None:
    """Test that content is auto-built from articles when not provided."""
    mock_article_repository.list_digest_eligible.return_value = sample_articles

    source = Source(
        id=sample_articles[0].source_id,
        name="Test Source",
        feed_url="https://example.com/feed",
        website_url=None,
        description=None,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    mock_source_repository.list_all.return_value = [source]
    mock_category_repository.list_all.return_value = []

    digest_id = uuid4()
    digest = Digest.create(
        title="Test Digest",
        content="auto-built content",
        digest_format=DigestFormat.MARKDOWN,
        article_ids=[article.id for article in sample_articles],
    )
    object.__setattr__(digest, "id", digest_id)

    mock_digest_repository.create.return_value = digest

    use_case = GenerateDigestUseCase(
        article_repository=mock_article_repository,
        digest_repository=mock_digest_repository,
        source_repository=mock_source_repository,
        category_repository=mock_category_repository,
    )

    result = await use_case.execute(
        title="Test Digest",
    )

    assert result.included_articles == 3
    call_args = mock_digest_repository.create.call_args
    created_digest = call_args[0][0]
    assert "Article 1" in created_digest.content
    assert "Article 2" in created_digest.content
    assert "Article 3" in created_digest.content
    assert "Test Source" in created_digest.content
