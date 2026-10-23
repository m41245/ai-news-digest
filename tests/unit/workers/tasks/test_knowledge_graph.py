"""
Unit tests for knowledge graph Celery tasks.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.workers.tasks.knowledge_graph import (
    extract_article_relationships,
    extract_story_cluster_relationships,
)
from tests.unit.workers.tasks.conftest import container_generator


class TestKnowledgeGraphTasks:
    @pytest.mark.asyncio
    async def test_article_relationships_success(self) -> None:
        article_id = uuid4()
        mock_container = MagicMock()
        use_case = MagicMock()
        use_case.extract_for_article = AsyncMock(return_value=[1, 2])
        mock_container.extract_relationships = use_case

        with patch(
            "ai_news_digest.workers.tasks.knowledge_graph.get_container",
            container_generator(mock_container),
        ):
            result = await extract_article_relationships(article_id)

        assert result["status"] == "completed"
        assert result["relationship_count"] == 2

    @pytest.mark.asyncio
    async def test_article_relationships_no_container(self) -> None:
        article_id = uuid4()

        async def empty_gen():
            for _ in ():
                yield _

        with patch(
            "ai_news_digest.workers.tasks.knowledge_graph.get_container",
            lambda: empty_gen(),
        ):
            result = await extract_article_relationships(article_id)

        assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_story_cluster_relationships_success(self) -> None:
        cluster_id = uuid4()
        mock_container = MagicMock()
        use_case = MagicMock()
        use_case.extract_for_story_cluster = AsyncMock(return_value=[1])
        mock_container.extract_relationships = use_case

        with patch(
            "ai_news_digest.workers.tasks.knowledge_graph.get_container",
            container_generator(mock_container),
        ):
            result = await extract_story_cluster_relationships(cluster_id)

        assert result["status"] == "completed"
        assert result["relationship_count"] == 1

    @pytest.mark.asyncio
    async def test_story_cluster_relationships_no_container(self) -> None:
        cluster_id = uuid4()

        async def empty_gen():
            for _ in ():
                yield _

        with patch(
            "ai_news_digest.workers.tasks.knowledge_graph.get_container",
            lambda: empty_gen(),
        ):
            result = await extract_story_cluster_relationships(cluster_id)

        assert result["status"] == "skipped"


__all__ = ["TestKnowledgeGraphTasks"]
