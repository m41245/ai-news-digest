"""
Unit tests for DigestRepository.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.infrastructure.database.repositories.digest_repository import DigestRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def repository(mock_session: AsyncMock) -> DigestRepository:
    """Create a DigestRepository instance."""
    return DigestRepository(mock_session)


@pytest.fixture
def sample_digest() -> Digest:
    """Create a sample Digest."""
    return Digest.create(
        title="Test Digest",
        content="Test content",
        digest_format=DigestFormat.MARKDOWN,
        article_ids=[uuid4(), uuid4()],
    )


@pytest.mark.asyncio
async def test_digest_repository_create(
    repository: DigestRepository, mock_session: AsyncMock, sample_digest: Digest
) -> None:
    """Test create method."""
    mock_result = MagicMock()
    mock_session.execute.return_value = mock_result
    mock_session.refresh = AsyncMock()

    with (
        patch.object(repository, "_add", new_callable=AsyncMock),
        patch.object(repository, "_flush", new_callable=AsyncMock),
        patch.object(repository, "_add_all", new_callable=AsyncMock),
        patch.object(repository, "_commit", new_callable=AsyncMock),
        patch(
            "ai_news_digest.infrastructure.database.repositories.digest_repository.DigestMapper.to_model"
        ) as mock_to_model,
        patch(
            "ai_news_digest.infrastructure.database.repositories.digest_repository.DigestMapper.to_domain"
        ) as mock_to_domain,
    ):
        mock_model = MagicMock()
        mock_model.id = str(sample_digest.id)
        mock_to_model.return_value = mock_model
        mock_to_domain.return_value = sample_digest

        result = await repository.create(sample_digest)

        assert result == sample_digest


@pytest.mark.asyncio
async def test_digest_repository_create_no_articles(
    repository: DigestRepository, mock_session: AsyncMock
) -> None:
    """Test create method with no article_ids."""
    digest = Digest.create(
        title="Test Digest",
        content="Test content",
        digest_format=DigestFormat.MARKDOWN,
        article_ids=[],
    )

    mock_result = MagicMock()
    mock_session.execute.return_value = mock_result
    mock_session.refresh = AsyncMock()

    with (
        patch.object(repository, "_add", new_callable=AsyncMock),
        patch.object(repository, "_flush", new_callable=AsyncMock),
        patch.object(repository, "_commit", new_callable=AsyncMock),
        patch(
            "ai_news_digest.infrastructure.database.repositories.digest_repository.DigestMapper.to_model"
        ) as mock_to_model,
        patch(
            "ai_news_digest.infrastructure.database.repositories.digest_repository.DigestMapper.to_domain"
        ) as mock_to_domain,
    ):
        mock_model = MagicMock()
        mock_model.id = str(digest.id)
        mock_to_model.return_value = mock_model
        mock_to_domain.return_value = digest

        result = await repository.create(digest)

        assert result == digest


@pytest.mark.asyncio
async def test_digest_repository_get_by_id_found(
    repository: DigestRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_id when digest is found."""
    digest_id = uuid4()
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.digest_repository.DigestMapper.to_domain"
    ) as mock_to_domain:
        mock_domain = MagicMock()
        mock_to_domain.return_value = mock_domain

        result = await repository.get_by_id(digest_id)

        assert result == mock_domain


@pytest.mark.asyncio
async def test_digest_repository_get_by_id_not_found(
    repository: DigestRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_id when digest is not found."""
    digest_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_id(digest_id)

    assert result is None


@pytest.mark.asyncio
async def test_digest_repository_list_recent(
    repository: DigestRepository, mock_session: AsyncMock
) -> None:
    """Test list_recent method."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_models = [MagicMock(), MagicMock()]
    mock_scalars.all.return_value = mock_models
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.digest_repository.DigestMapper.to_domain"
    ) as mock_to_domain:
        mock_to_domain.side_effect = lambda m: m

        result = await repository.list_recent(limit=10)

        assert len(result) == 2


@pytest.mark.asyncio
async def test_digest_repository_update_found(
    repository: DigestRepository, mock_session: AsyncMock, sample_digest: Digest
) -> None:
    """Test update when digest is found."""
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    mock_session.refresh = AsyncMock()

    with (
        patch(
            "ai_news_digest.infrastructure.database.repositories.digest_repository.DigestMapper.update_model"
        ),
        patch.object(repository, "_commit", new_callable=AsyncMock),
        patch.object(repository, "_add_all", new_callable=AsyncMock),
        patch(
            "ai_news_digest.infrastructure.database.repositories.digest_repository.DigestMapper.to_domain"
        ) as mock_to_domain,
    ):
        mock_to_domain.return_value = sample_digest

        result = await repository.update(sample_digest)

        assert result == sample_digest


@pytest.mark.asyncio
async def test_digest_repository_update_not_found(
    repository: DigestRepository, mock_session: AsyncMock, sample_digest: Digest
) -> None:
    """Test update when digest is not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(ResourceNotFoundError, match="was not found"):
        await repository.update(sample_digest)


@pytest.mark.asyncio
async def test_digest_repository_delete_found(
    repository: DigestRepository, mock_session: AsyncMock
) -> None:
    """Test delete when digest is found."""
    digest_id = uuid4()
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch.object(repository, "_delete", new_callable=AsyncMock):
        await repository.delete(digest_id)


@pytest.mark.asyncio
async def test_digest_repository_delete_not_found(
    repository: DigestRepository, mock_session: AsyncMock
) -> None:
    """Test delete when digest is not found."""
    digest_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    await repository.delete(digest_id)  # Should not raise


@pytest.mark.asyncio
async def test_digest_repository_rollback(
    repository: DigestRepository, mock_session: AsyncMock
) -> None:
    """Test rollback delegates to session rollback."""
    with patch.object(mock_session, "rollback", new_callable=AsyncMock) as mock_rollback:
        await repository.rollback()
        mock_rollback.assert_awaited_once()


__all__ = [
    "test_digest_repository_create",
    "test_digest_repository_create_no_articles",
    "test_digest_repository_delete_found",
    "test_digest_repository_delete_not_found",
    "test_digest_repository_get_by_id_found",
    "test_digest_repository_get_by_id_not_found",
    "test_digest_repository_list_recent",
    "test_digest_repository_rollback",
    "test_digest_repository_update_found",
    "test_digest_repository_update_not_found",
]
