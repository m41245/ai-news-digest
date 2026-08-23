"""
Unit tests for CreateSourceUseCase.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from ai_news_digest.application.dto.source import CreateSourceRequest
from ai_news_digest.application.exceptions.source import SourceAlreadyExistsError
from ai_news_digest.application.use_cases.source.create import CreateSourceUseCase
from ai_news_digest.domain.models.source import Source


async def test_create_source_success(mock_source_repository: AsyncMock) -> None:
    """Test successful source creation."""
    # Arrange
    request = CreateSourceRequest(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test description",
        is_active=True,
    )

    mock_source_repository.get_by_feed_url.return_value = None
    created_source = Source.create(
        name=request.name,
        feed_url=request.feed_url,
        website_url=request.website_url,
        description=request.description,
        is_active=request.is_active,
    )
    mock_source_repository.create.return_value = created_source

    use_case = CreateSourceUseCase(repository=mock_source_repository)

    # Act
    response = await use_case.execute(request)

    # Assert
    assert response.name == "Test Source"
    assert response.feed_url == "https://example.com/feed.xml"
    assert response.website_url == "https://example.com"
    assert response.description == "Test description"
    assert response.is_active is True
    mock_source_repository.get_by_feed_url.assert_called_once_with(request.feed_url)
    mock_source_repository.create.assert_called_once()


async def test_create_source_duplicate_feed_url(mock_source_repository: AsyncMock) -> None:
    """Test source creation fails when feed URL already exists."""
    # Arrange
    request = CreateSourceRequest(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test description",
        is_active=True,
    )

    existing_source = Source.create(
        name="Existing Source",
        feed_url="https://example.com/feed.xml",
        is_active=True,
    )
    mock_source_repository.get_by_feed_url.return_value = existing_source

    use_case = CreateSourceUseCase(repository=mock_source_repository)

    # Act & Assert
    with pytest.raises(SourceAlreadyExistsError, match=r"https://example.com/feed.xml"):
        await use_case.execute(request)

    mock_source_repository.create.assert_not_called()


async def test_create_source_minimal(mock_source_repository: AsyncMock) -> None:
    """Test source creation with minimal parameters."""
    # Arrange
    request = CreateSourceRequest(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
    )

    mock_source_repository.get_by_feed_url.return_value = None
    created_source = Source.create(
        name=request.name,
        feed_url=request.feed_url,
        is_active=True,
    )
    mock_source_repository.create.return_value = created_source

    use_case = CreateSourceUseCase(repository=mock_source_repository)

    # Act
    response = await use_case.execute(request)

    # Assert
    assert response.name == "Test Source"
    assert response.feed_url == "https://example.com/feed.xml"
    assert response.website_url is None
    assert response.description is None
    assert response.is_active is True
