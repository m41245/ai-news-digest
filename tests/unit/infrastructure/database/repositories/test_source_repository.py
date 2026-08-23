"""
Unit tests for SourceRepository.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.source import Source
from ai_news_digest.infrastructure.database.repositories.source_repository import SourceRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def repository(mock_session: AsyncMock) -> SourceRepository:
    """Create a SourceRepository instance."""
    return SourceRepository(mock_session)


@pytest.fixture
def sample_source() -> Source:
    """Create a sample Source."""
    return Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test description",
    )


@pytest.mark.asyncio
async def test_source_repository_create(
    repository: SourceRepository, mock_session: AsyncMock, sample_source: Source
) -> None:
    """Test create method."""
    mock_result = MagicMock()
    mock_session.execute.return_value = mock_result
    mock_session.refresh = AsyncMock()

    with patch.object(repository, "_add_and_refresh", new_callable=AsyncMock) as mock_add_refresh:
        mock_model = MagicMock()
        mock_model.id = str(sample_source.id)
        mock_add_refresh.return_value = mock_model

        with patch(
            "ai_news_digest.infrastructure.database.repositories.source_repository.SourceMapper.to_model"
        ) as mock_to_model:
            mock_to_model.return_value = mock_model

            with patch(
                "ai_news_digest.infrastructure.database.repositories.source_repository.SourceMapper.to_domain"
            ) as mock_to_domain:
                mock_to_domain.return_value = sample_source

                result = await repository.create(sample_source)

                assert result == sample_source


@pytest.mark.asyncio
async def test_source_repository_get_by_id_found(
    repository: SourceRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_id when source is found."""
    source_id = uuid4()
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.source_repository.SourceMapper.to_domain"
    ) as mock_to_domain:
        mock_domain = MagicMock()
        mock_to_domain.return_value = mock_domain

        result = await repository.get_by_id(source_id)

        assert result == mock_domain


@pytest.mark.asyncio
async def test_source_repository_get_by_id_not_found(
    repository: SourceRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_id when source is not found."""
    source_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_id(source_id)

    assert result is None


@pytest.mark.asyncio
async def test_source_repository_get_by_feed_url_found(
    repository: SourceRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_feed_url when source is found."""
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.source_repository.SourceMapper.to_domain"
    ) as mock_to_domain:
        mock_domain = MagicMock()
        mock_to_domain.return_value = mock_domain

        result = await repository.get_by_feed_url("https://example.com/feed.xml")

        assert result == mock_domain


@pytest.mark.asyncio
async def test_source_repository_get_by_feed_url_not_found(
    repository: SourceRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_feed_url when source is not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_feed_url("https://example.com/feed.xml")

    assert result is None


@pytest.mark.asyncio
async def test_source_repository_list_all(
    repository: SourceRepository, mock_session: AsyncMock
) -> None:
    """Test list_all method."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_models = [MagicMock(), MagicMock()]
    mock_scalars.all.return_value = mock_models
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.source_repository.SourceMapper.to_domain"
    ) as mock_to_domain:
        mock_to_domain.side_effect = lambda m: m

        result = await repository.list_all()

        assert len(result) == 2


@pytest.mark.asyncio
async def test_source_repository_list_enabled(
    repository: SourceRepository, mock_session: AsyncMock
) -> None:
    """Test list_enabled method."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_models = [MagicMock(), MagicMock()]
    mock_scalars.all.return_value = mock_models
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.source_repository.SourceMapper.to_domain"
    ) as mock_to_domain:
        mock_to_domain.side_effect = lambda m: m

        result = await repository.list_enabled()

        assert len(result) == 2


@pytest.mark.asyncio
async def test_source_repository_list_active(repository: SourceRepository) -> None:
    """Test list_active method (alias for list_enabled)."""
    with patch.object(repository, "list_enabled", new_callable=AsyncMock) as mock_list_enabled:
        mock_list_enabled.return_value = [MagicMock()]

        await repository.list_active()

        mock_list_enabled.assert_called_once()


@pytest.mark.asyncio
async def test_source_repository_update_found(
    repository: SourceRepository, mock_session: AsyncMock, sample_source: Source
) -> None:
    """Test update when source is found."""
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    mock_session.refresh = AsyncMock()

    with (
        patch(
            "ai_news_digest.infrastructure.database.repositories.source_repository.SourceMapper.update_model"
        ),
        patch(
            "ai_news_digest.infrastructure.database.repositories.source_repository.SourceMapper.to_domain"
        ) as mock_to_domain,
    ):
        mock_to_domain.return_value = sample_source

        result = await repository.update(sample_source)

        assert result == sample_source


@pytest.mark.asyncio
async def test_source_repository_update_not_found(
    repository: SourceRepository, mock_session: AsyncMock, sample_source: Source
) -> None:
    """Test update when source is not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(ResourceNotFoundError, match="was not found"):
        await repository.update(sample_source)


@pytest.mark.asyncio
async def test_source_repository_delete_found(
    repository: SourceRepository, mock_session: AsyncMock
) -> None:
    """Test delete when source is found."""
    source_id = uuid4()
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch.object(repository, "_delete", new_callable=AsyncMock):
        await repository.delete(source_id)


@pytest.mark.asyncio
async def test_source_repository_delete_not_found(
    repository: SourceRepository, mock_session: AsyncMock
) -> None:
    """Test delete when source is not found."""
    source_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    await repository.delete(source_id)  # Should not raise
