"""
Unit tests for CategoryRepository.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.category import Category
from ai_news_digest.infrastructure.database.repositories.category_repository import (
    CategoryRepository,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def repository(mock_session: AsyncMock) -> CategoryRepository:
    """Create a CategoryRepository instance."""
    return CategoryRepository(mock_session)


@pytest.fixture
def sample_category() -> Category:
    """Create a sample Category."""
    return Category.create(
        name="Technology",
        description="Technology news and updates",
    )


@pytest.mark.asyncio
async def test_category_repository_create(
    repository: CategoryRepository, mock_session: AsyncMock, sample_category: Category
) -> None:
    """Test create method."""
    mock_result = MagicMock()
    mock_session.execute.return_value = mock_result
    mock_session.refresh = AsyncMock()

    with patch.object(repository, "_add_and_refresh", new_callable=AsyncMock) as mock_add_refresh:
        mock_model = MagicMock()
        mock_model.id = str(sample_category.id)
        mock_add_refresh.return_value = mock_model

        with patch(
            "ai_news_digest.infrastructure.database.repositories.category_repository.CategoryMapper.to_model"
        ) as mock_to_model:
            mock_to_model.return_value = mock_model

            with patch(
                "ai_news_digest.infrastructure.database.repositories.category_repository.CategoryMapper.to_domain"
            ) as mock_to_domain:
                mock_to_domain.return_value = sample_category

                result = await repository.create(sample_category)

                assert result == sample_category


@pytest.mark.asyncio
async def test_category_repository_get_by_id_found(
    repository: CategoryRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_id when category is found."""
    category_id = uuid4()
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.category_repository.CategoryMapper.to_domain"
    ) as mock_to_domain:
        mock_domain = MagicMock()
        mock_to_domain.return_value = mock_domain

        result = await repository.get_by_id(category_id)

        assert result == mock_domain


@pytest.mark.asyncio
async def test_category_repository_get_by_id_not_found(
    repository: CategoryRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_id when category is not found."""
    category_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_id(category_id)

    assert result is None


@pytest.mark.asyncio
async def test_category_repository_get_by_name_found(
    repository: CategoryRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_name when category is found."""
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.category_repository.CategoryMapper.to_domain"
    ) as mock_to_domain:
        mock_domain = MagicMock()
        mock_to_domain.return_value = mock_domain

        result = await repository.get_by_name("Technology")

        assert result == mock_domain


@pytest.mark.asyncio
async def test_category_repository_get_by_name_not_found(
    repository: CategoryRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_name when category is not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_name("Technology")

    assert result is None


@pytest.mark.asyncio
async def test_category_repository_list(
    repository: CategoryRepository, mock_session: AsyncMock
) -> None:
    """Test list method."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_models = [MagicMock(), MagicMock()]
    mock_scalars.all.return_value = mock_models
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.category_repository.CategoryMapper.to_domain"
    ) as mock_to_domain:
        mock_to_domain.side_effect = lambda m: m

        result = await repository.list_all()

        assert len(result) == 2


@pytest.mark.asyncio
async def test_category_repository_list_empty(
    repository: CategoryRepository, mock_session: AsyncMock
) -> None:
    """Test list when no categories exist."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    result = await repository.list_all()

    assert len(result) == 0


@pytest.mark.asyncio
async def test_category_repository_update_found(
    repository: CategoryRepository, mock_session: AsyncMock, sample_category: Category
) -> None:
    """Test update when category is found."""
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    mock_session.refresh = AsyncMock()

    with (
        patch(
            "ai_news_digest.infrastructure.database.repositories.category_repository.CategoryMapper.update_model"
        ),
        patch(
            "ai_news_digest.infrastructure.database.repositories.category_repository.CategoryMapper.to_domain"
        ) as mock_to_domain,
    ):
        mock_to_domain.return_value = sample_category

        result = await repository.update(sample_category)

        assert result == sample_category


@pytest.mark.asyncio
async def test_category_repository_update_not_found(
    repository: CategoryRepository, mock_session: AsyncMock, sample_category: Category
) -> None:
    """Test update when category is not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(ResourceNotFoundError, match="was not found"):
        await repository.update(sample_category)


@pytest.mark.asyncio
async def test_category_repository_delete_found(
    repository: CategoryRepository, mock_session: AsyncMock
) -> None:
    """Test delete when category is found."""
    category_id = uuid4()
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch.object(repository, "_delete", new_callable=AsyncMock):
        await repository.delete(category_id)


@pytest.mark.asyncio
async def test_category_repository_delete_not_found(
    repository: CategoryRepository, mock_session: AsyncMock
) -> None:
    """Test delete when category is not found."""
    category_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    await repository.delete(category_id)  # Should not raise
