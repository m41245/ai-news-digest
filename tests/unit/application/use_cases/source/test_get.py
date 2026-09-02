"""
Unit tests for GetSourceUseCase.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ai_news_digest.application.exceptions.source import SourceNotFoundError
from ai_news_digest.application.use_cases.source.get import GetSourceUseCase
from ai_news_digest.domain.models.source import Source


async def test_get_source_success(mock_source_repository: AsyncMock) -> None:
    """Test successful source retrieval."""
    # Arrange
    source_id = uuid4()
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test description",
        is_active=True,
    )
    mock_source_repository.get_by_id.return_value = source

    use_case = GetSourceUseCase(repository=mock_source_repository)

    # Act
    response = await use_case.execute(source_id)

    # Assert
    assert response.name == "Test Source"
    assert response.feed_url == "https://example.com/feed.xml"
    assert response.website_url == "https://example.com"
    assert response.description == "Test description"
    assert response.is_active is True
    mock_source_repository.get_by_id.assert_called_once_with(source_id)


async def test_get_source_not_found(mock_source_repository: AsyncMock) -> None:
    """Test source retrieval fails when source does not exist."""
    # Arrange
    source_id = uuid4()
    mock_source_repository.get_by_id.return_value = None

    use_case = GetSourceUseCase(repository=mock_source_repository)

    # Act & Assert
    with pytest.raises(SourceNotFoundError, match=str(source_id)):
        await use_case.execute(source_id)
