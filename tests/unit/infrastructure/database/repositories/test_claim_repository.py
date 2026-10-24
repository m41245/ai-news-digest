"""
Unit tests for ClaimRepository.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.infrastructure.database.repositories.claim_repository import (
    SqlAlchemyClaimRepository,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repository(mock_session: AsyncMock) -> SqlAlchemyClaimRepository:
    return SqlAlchemyClaimRepository(mock_session)


@pytest.mark.asyncio
async def test_claim_repository_list_by_article_id(
    repository: SqlAlchemyClaimRepository, mock_session: AsyncMock
) -> None:
    model = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [model]
    mock_session.execute.return_value = result
    claim = MagicMock()
    with patch(
        "ai_news_digest.infrastructure.database.repositories.claim_repository.ClaimMapper.to_domain",
        return_value=claim,
    ):
        assert await repository.list_by_article_id(uuid4()) == [claim]
