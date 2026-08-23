"""
Unit tests for DeleteSourceUseCase.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ai_news_digest.application.exceptions.source import SourceNotFoundError
from ai_news_digest.application.use_cases.source.delete import DeleteSourceUseCase
from ai_news_digest.domain.models.source import Source


async def test_delete_source_success(mock_source_repository: AsyncMock) -> None:
    """Test successful source deletion."""
    # Arrange
    source_id = uuid4()
    existing_source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        is_active=True,
    )
    mock_source_repository.get_by_id.return_value = existing_source
    mock_source_repository.delete.return_value = None

    use_case = DeleteSourceUseCase(repository=mock_source_repository)

    # Act
    await use_case.execute(source_id)

    # Assert
    mock_source_repository.get_by_id.assert_called_once_with(source_id)
    mock_source_repository.delete.assert_called_once_with(source_id)


async def test_delete_source_not_found(mock_source_repository: AsyncMock) -> None:
    """Test source deletion fails when source does not exist."""
    # Arrange
    source_id = uuid4()
    mock_source_repository.get_by_id.return_value = None

    use_case = DeleteSourceUseCase(repository=mock_source_repository)

    # Act & Assert
    with pytest.raises(SourceNotFoundError, match=str(source_id)):
        await use_case.execute(source_id)

    mock_source_repository.delete.assert_not_called()
