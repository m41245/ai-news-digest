"""
Unit tests for ListSourcesUseCase.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from ai_news_digest.application.use_cases.source.list import ListSourcesUseCase
from ai_news_digest.domain.models.source import Source


async def test_list_sources_success(mock_source_repository: AsyncMock) -> None:
    """Test successful listing of all sources."""
    # Arrange
    sources = [
        Source.create(
            name="Source A",
            feed_url="https://a.com/feed.xml",
            is_active=True,
        ),
        Source.create(
            name="Source B",
            feed_url="https://b.com/feed.xml",
            is_active=False,
        ),
        Source.create(
            name="Source C",
            feed_url="https://c.com/feed.xml",
            is_active=True,
        ),
    ]
    mock_source_repository.list_all.return_value = sources

    use_case = ListSourcesUseCase(repository=mock_source_repository)

    # Act
    responses = await use_case.execute()

    # Assert
    assert len(responses) == 3
    assert responses[0].name == "Source A"
    assert responses[1].name == "Source B"
    assert responses[2].name == "Source C"
    mock_source_repository.list_all.assert_called_once()


async def test_list_sources_empty(mock_source_repository: AsyncMock) -> None:
    """Test listing sources when none exist."""
    # Arrange
    mock_source_repository.list_all.return_value = []

    use_case = ListSourcesUseCase(repository=mock_source_repository)

    # Act
    responses = await use_case.execute()

    # Assert
    assert len(responses) == 0
    mock_source_repository.list_all.assert_called_once()
