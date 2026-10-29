"""Unit tests for CompanyRepository consistency contract."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.company import Company
from ai_news_digest.infrastructure.database.repositories.company_repository import (
    SqlAlchemyCompanyRepository,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repository(mock_session: AsyncMock) -> SqlAlchemyCompanyRepository:
    return SqlAlchemyCompanyRepository(mock_session)


@pytest.mark.asyncio
async def test_list_all_with_counts_maps_to_domain(
    repository: SqlAlchemyCompanyRepository, mock_session: AsyncMock
) -> None:
    model = MagicMock()
    model.id = str(uuid4())
    model.name = "Acme"
    model.created_at = MagicMock()
    model.slug = "acme"
    mock_result = MagicMock()
    mock_result.all.return_value = [(model, 5)]
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.company_repository.CompanyMapper.to_domain"
    ) as mock_to_domain:
        domain = Company(
            id=uuid4(),
            name="Acme",
            created_at=model.created_at,
            slug="acme",
        )
        mock_to_domain.return_value = domain
        result = await repository.list_all_with_counts()

    assert len(result) == 1
    assert result[0] is domain
    assert result[0].article_count == 5


@pytest.mark.asyncio
async def test_update_found_returns_domain(
    repository: SqlAlchemyCompanyRepository, mock_session: AsyncMock
) -> None:
    company_id = uuid4()
    company = Company(id=company_id, name="Renamed", created_at=MagicMock(), slug="renamed")
    model = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = model
    mock_session.execute.return_value = mock_result
    mock_session.flush = AsyncMock()

    with (
        patch(
            "ai_news_digest.infrastructure.database.repositories.company_repository.CompanyMapper.update_model"
        ),
        patch(
            "ai_news_digest.infrastructure.database.repositories.company_repository.CompanyMapper.to_domain"
        ) as mock_to_domain,
    ):
        mock_to_domain.return_value = company
        result = await repository.update(company)

    assert result == company


@pytest.mark.asyncio
async def test_update_not_found_raises(
    repository: SqlAlchemyCompanyRepository, mock_session: AsyncMock
) -> None:
    company = Company(id=uuid4(), name="Missing", created_at=MagicMock())
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(ResourceNotFoundError):
        await repository.update(company)
