"""Unit tests for TopicRepository consistency contract."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.topic import Topic
from ai_news_digest.infrastructure.database.repositories.topic_repository import (
    SqlAlchemyTopicRepository,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repository(mock_session: AsyncMock) -> SqlAlchemyTopicRepository:
    return SqlAlchemyTopicRepository(mock_session)


@pytest.mark.asyncio
async def test_list_all_with_counts_maps_to_domain(
    repository: SqlAlchemyTopicRepository, mock_session: AsyncMock
) -> None:
    model = MagicMock()
    model.id = str(uuid4())
    model.name = "AI"
    model.created_at = MagicMock()
    model.slug = "ai"
    mock_result = MagicMock()
    mock_result.all.return_value = [(model, 10)]
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.topic_repository.TopicMapper.to_domain"
    ) as mock_to_domain:
        domain = Topic(
            id=uuid4(),
            name="AI",
            created_at=model.created_at,
            slug="ai",
        )
        mock_to_domain.return_value = domain
        result = await repository.list_all_with_counts()

    assert len(result) == 1
    assert result[0] is domain
    assert result[0].article_count == 10


@pytest.mark.asyncio
async def test_update_found_returns_domain(
    repository: SqlAlchemyTopicRepository, mock_session: AsyncMock
) -> None:
    topic = Topic(id=uuid4(), name="Renamed", created_at=MagicMock(), slug="renamed")
    model = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = model
    mock_session.execute.return_value = mock_result
    mock_session.flush = AsyncMock()

    with (
        patch(
            "ai_news_digest.infrastructure.database.repositories.topic_repository.TopicMapper.update_model"
        ),
        patch(
            "ai_news_digest.infrastructure.database.repositories.topic_repository.TopicMapper.to_domain"
        ) as mock_to_domain,
    ):
        mock_to_domain.return_value = topic
        result = await repository.update(topic)

    assert result == topic


@pytest.mark.asyncio
async def test_update_not_found_raises(
    repository: SqlAlchemyTopicRepository, mock_session: AsyncMock
) -> None:
    topic = Topic(id=uuid4(), name="Missing", created_at=MagicMock())
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(ResourceNotFoundError):
        await repository.update(topic)
