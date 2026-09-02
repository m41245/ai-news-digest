"""
Unit tests for ListEnabledSourcesUseCase.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from ai_news_digest.application.use_cases.source.list_enabled import (
    ListEnabledSourcesUseCase,
)
from ai_news_digest.domain.models.source import Source


async def test_list_enabled_sources_success(mock_source_repository: AsyncMock) -> None:
    """Test successful listing of enabled sources."""
    # Arrange
    sources = [
        Source.create(
            name="Active Source 1",
            feed_url="https://active1.com/feed.xml",
            is_active=True,
        ),
        Source.create(
            name="Active Source 2",
            feed_url="https://active2.com/feed.xml",
            is_active=True,
        ),
    ]
    mock_source_repository.list_enabled.return_value = sources

    use_case = ListEnabledSourcesUseCase(repository=mock_source_repository)

    # Act
    responses = await use_case.execute()

    # Assert
    assert len(responses) == 2
    assert responses[0].name == "Active Source 1"
    assert responses[1].name == "Active Source 2"
    assert all(response.is_active for response in responses)
    mock_source_repository.list_enabled.assert_called_once()


async def test_list_enabled_sources_empty(mock_source_repository: AsyncMock) -> None:
    """Test listing enabled sources when none exist."""
    # Arrange
    mock_source_repository.list_enabled.return_value = []

    use_case = ListEnabledSourcesUseCase(repository=mock_source_repository)

    # Act
    responses = await use_case.execute()

    # Assert
    assert len(responses) == 0
    mock_source_repository.list_enabled.assert_called_once()


async def test_list_enabled_sources_filters_inactive(mock_source_repository: AsyncMock) -> None:
    """Test that inactive sources are not included."""
    # Arrange
    sources = [
        Source.create(
            name="Active Source",
            feed_url="https://active.com/feed.xml",
            is_active=True,
        ),
    ]
    mock_source_repository.list_enabled.return_value = sources

    use_case = ListEnabledSourcesUseCase(repository=mock_source_repository)

    # Act
    responses = await use_case.execute()

    # Assert
    assert len(responses) == 1
    assert responses[0].is_active is True
