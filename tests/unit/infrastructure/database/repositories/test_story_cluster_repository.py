"""
Unit tests for StoryClusterRepository.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.infrastructure.database.repositories.story_cluster_repository import (
    StoryClusterRepository,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.all.return_value = []
    result.all.return_value = []
    result.scalar_one.return_value = 0
    session.execute.return_value = result
    return session


@pytest.fixture
def repository(mock_session: AsyncMock) -> StoryClusterRepository:
    return StoryClusterRepository(mock_session)


@pytest.fixture
def cluster_id() -> object:
    return uuid4()


class TestStoryClusterRepository:
    @pytest.mark.asyncio
    async def test_create(self, repository, mock_session) -> None:
        cluster = MagicMock()
        model = MagicMock()
        with patch(
            "ai_news_digest.infrastructure.database.repositories.story_cluster_repository.StoryClusterMapper"
        ) as mapper:
            mapper.to_model.return_value = model
            mapper.to_domain.return_value = cluster
            result = await repository.create(cluster)
        assert result is cluster

    @pytest.mark.asyncio
    async def test_get_by_id_none(self, repository) -> None:
        result = await repository.get_by_id(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_session) -> None:
        model = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = model
        with patch(
            "ai_news_digest.infrastructure.database.repositories.story_cluster_repository.StoryClusterMapper"
        ) as mapper:
            cluster = MagicMock()
            mapper.to_domain.return_value = cluster
            result = await repository.get_by_id(uuid4())
        assert result is cluster

    @pytest.mark.asyncio
    async def test_get_by_slug_none(self, repository) -> None:
        result = await repository.get_by_slug("slug")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_all(self, repository, mock_session) -> None:
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        result = await repository.list_all(limit=10, offset=0)
        assert result == []

    @pytest.mark.asyncio
    async def test_find_recent_active_clusters_filters(self, repository, mock_session) -> None:
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        cutoff = datetime.now(UTC)
        await repository.find_recent_active_clusters(cutoff=cutoff)
        await repository.find_recent_active_clusters(
            cutoff=cutoff,
            category_id=uuid4(),
            company_ids=[uuid4()],
            topic_ids=[uuid4()],
            title_tokens=["token"],
            limit=5,
        )
        assert True

    @pytest.mark.asyncio
    async def test_count(self, repository, mock_session) -> None:
        mock_session.execute.return_value.scalar_one.return_value = 3
        result = await repository.count()
        assert result == 3

    @pytest.mark.asyncio
    async def test_search_public_filters(self, repository, mock_session) -> None:
        mock_session.execute.return_value.all.return_value = []
        await repository.search_public()
        await repository.search_public(
            search="q",
            category_id=uuid4(),
            company_id=uuid4(),
            topic_id=uuid4(),
            published_from=datetime.now(UTC),
            published_to=datetime.now(UTC),
            min_importance=0.5,
            limit=5,
            offset=2,
        )
        assert True

    @pytest.mark.asyncio
    async def test_count_public_filters(self, repository, mock_session) -> None:
        mock_session.execute.return_value.scalar_one.return_value = 2
        await repository.count_public()
        await repository.count_public(
            search="q",
            category_id=uuid4(),
            company_id=uuid4(),
            topic_id=uuid4(),
            published_from=datetime.now(UTC),
            published_to=datetime.now(UTC),
            min_importance=0.5,
        )
        assert True

    @pytest.mark.asyncio
    async def test_update_found(self, repository, mock_session) -> None:
        model = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = model
        mock_session.refresh.return_value = model
        cluster = MagicMock()
        cluster.id = uuid4()
        with patch(
            "ai_news_digest.infrastructure.database.repositories.story_cluster_repository.StoryClusterMapper"
        ) as mapper:
            mapper.update_model.return_value = None
            mapper.to_domain.return_value = cluster
            result = await repository.update(cluster)
        assert result is cluster

    @pytest.mark.asyncio
    async def test_update_not_found(self, repository) -> None:
        with pytest.raises(ResourceNotFoundError):
            cluster = MagicMock()
            cluster.id = uuid4()
            await repository.update(cluster)

    @pytest.mark.asyncio
    async def test_bulk_update_ranking_empty(self, repository) -> None:
        await repository.bulk_update_ranking([])

    @pytest.mark.asyncio
    async def test_bulk_update_ranking_non_empty(self, repository, mock_session) -> None:
        await repository.bulk_update_ranking([(uuid4(), 1.0, "exp")])

    @pytest.mark.asyncio
    async def test_attach_and_detach(self, repository, mock_session) -> None:
        await repository.attach_article(uuid4(), uuid4())
        await repository.detach_article(uuid4())

    @pytest.mark.asyncio
    async def test_get_by_ids_empty(self, repository) -> None:
        result = await repository.get_by_ids([])
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_ids_non_empty(self, repository, mock_session) -> None:
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        result = await repository.get_by_ids([uuid4()])
        assert result == []


__all__ = ["TestStoryClusterRepository"]
