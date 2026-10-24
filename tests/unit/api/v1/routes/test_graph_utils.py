"""
Unit tests for graph utils.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.api.v1.routes._graph_utils import build_graph_name_map


class TestBuildGraphNameMap:
    @pytest.mark.asyncio
    async def test_builds_name_map(self) -> None:
        company_id = uuid4()
        topic_id = uuid4()
        category_id = uuid4()
        story_id = uuid4()

        company = SimpleNamespace(id=company_id, name="Acme")
        topic = SimpleNamespace(id=topic_id, name="AI")
        category = SimpleNamespace(id=category_id, name="Tech")
        cluster = SimpleNamespace(id=story_id, title="Story")

        container = MagicMock()
        container.company_repository.list_by_ids = AsyncMock(return_value=[company])
        container.topic_repository.list_by_ids = AsyncMock(return_value=[topic])
        container.category_repository.list_by_ids = AsyncMock(return_value=[category])
        container.story_cluster_repository.get_by_ids = AsyncMock(return_value=[cluster])

        rel = SimpleNamespace(
            object_entity_type=SimpleNamespace(value="company"),
            object_entity_id=company_id,
            subject_entity_type=SimpleNamespace(value="topic"),
            subject_entity_id=topic_id,
        )
        # add category/story via another rel
        rel2 = SimpleNamespace(
            object_entity_type=SimpleNamespace(value="category"),
            object_entity_id=category_id,
            subject_entity_type=SimpleNamespace(value="story"),
            subject_entity_id=story_id,
        )

        result = await build_graph_name_map(container, [rel, rel2])
        assert result[f"company:{company_id}"] == "Acme"
        assert result[f"topic:{topic_id}"] == "AI"
        assert result[f"category:{category_id}"] == "Tech"
        assert result[f"story:{story_id}"] == "Story"

    @pytest.mark.asyncio
    async def test_empty_relationships(self) -> None:
        container = MagicMock()
        container.company_repository.list_by_ids = AsyncMock(return_value=[])
        container.topic_repository.list_by_ids = AsyncMock(return_value=[])
        container.category_repository.list_by_ids = AsyncMock(return_value=[])
        container.story_cluster_repository.get_by_ids = AsyncMock(return_value=[])
        result = await build_graph_name_map(container, [])
        assert result == {}


__all__ = ["TestBuildGraphNameMap"]
