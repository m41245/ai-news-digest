"""
Unit tests for UpdateSourceUseCase.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ai_news_digest.application.dto.source import UpdateSourceRequest
from ai_news_digest.application.exceptions.source import SourceNotFoundError
from ai_news_digest.application.use_cases.source.update import UpdateSourceUseCase
from ai_news_digest.domain.models.source import Source


async def test_update_source_success(mock_source_repository: AsyncMock) -> None:
    """Test successful source update."""
    # Arrange
    source_id = uuid4()
    request = UpdateSourceRequest(
        id=source_id,
        name="Updated Name",
        feed_url="https://updated.com/feed.xml",
        website_url="https://updated.com",
        description="Updated description",
        is_active=False,
    )

    existing_source = Source.create(
        name="Original Name",
        feed_url="https://original.com/feed.xml",
        is_active=True,
    )
    mock_source_repository.get_by_id.return_value = existing_source
    mock_source_repository.update.return_value = existing_source

    use_case = UpdateSourceUseCase(repository=mock_source_repository)

    # Act
    response = await use_case.execute(request)

    # Assert
    assert response.name == "Updated Name"
    assert response.feed_url == "https://updated.com/feed.xml"
    assert response.website_url == "https://updated.com"
    assert response.description == "Updated description"
    assert response.is_active is False
    mock_source_repository.get_by_id.assert_called_once_with(source_id)
    mock_source_repository.update.assert_called_once()


async def test_update_source_not_found(mock_source_repository: AsyncMock) -> None:
    """Test source update fails when source does not exist."""
    # Arrange
    source_id = uuid4()
    request = UpdateSourceRequest(
        id=source_id,
        name="Updated Name",
        feed_url="https://updated.com/feed.xml",
    )

    mock_source_repository.get_by_id.return_value = None

    use_case = UpdateSourceUseCase(repository=mock_source_repository)

    # Act & Assert
    with pytest.raises(SourceNotFoundError, match=str(source_id)):
        await use_case.execute(request)

    mock_source_repository.update.assert_not_called()


async def test_update_source_partial(mock_source_repository: AsyncMock) -> None:
    """Test partial source update."""
    # Arrange
    source_id = uuid4()
    request = UpdateSourceRequest(
        id=source_id,
        name="Updated Name Only",
    )

    existing_source = Source.create(
        name="Original Name",
        feed_url="https://original.com/feed.xml",
        website_url="https://original.com",
        description="Original description",
        is_active=True,
    )
    mock_source_repository.get_by_id.return_value = existing_source
    mock_source_repository.update.return_value = existing_source

    use_case = UpdateSourceUseCase(repository=mock_source_repository)

    # Act
    response = await use_case.execute(request)

    # Assert
    assert response.name == "Updated Name Only"
    # Other fields should remain unchanged
    assert response.feed_url == "https://original.com/feed.xml"
    assert response.website_url == "https://original.com"
    assert response.description == "Original description"
    assert response.is_active is True
