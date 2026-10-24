"""
Unit tests for LLM story activity helpers.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_news_digest.application.evaluation.story_activity_llm import (
    LLMStoryActivityResult,
    run_llm_story_activity_check,
)


def _activity() -> SimpleNamespace:
    return SimpleNamespace(
        activity_score=0.5,
        status=SimpleNamespace(value="DEVELOPING"),
        article_count_recent=3,
        unique_source_count_recent=2,
        recent_article_velocity=1.0,
        recent_claim_count=4,
        recent_conflict_count=1,
        state_change_count=2,
        explanation="recent updates",
    )


def _cluster() -> SimpleNamespace:
    return SimpleNamespace(title="Story", summary="Summary")


class TestRunLLMStoryActivityCheck:
    @pytest.mark.asyncio
    async def test_empty_content_returns_none(self) -> None:
        pm = MagicMock()
        pm.generate = AsyncMock(return_value=SimpleNamespace(content="", text=""))
        result = await run_llm_story_activity_check(
            activity=_activity(), cluster=_cluster(), provider_manager=pm
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_json_returns_none(self) -> None:
        pm = MagicMock()
        pm.generate = AsyncMock(return_value=SimpleNamespace(content="not json", text=""))
        result = await run_llm_story_activity_check(
            activity=_activity(), cluster=_cluster(), provider_manager=pm
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_status_returns_result(self) -> None:
        pm = MagicMock()
        pm.generate = AsyncMock(
            return_value=SimpleNamespace(
                content='{"status":"BREAKING","confidence":0.9,"reason":"r","meaningful_update":true}',
                text="",
            )
        )
        result = await run_llm_story_activity_check(
            activity=_activity(), cluster=_cluster(), provider_manager=pm
        )
        assert isinstance(result, LLMStoryActivityResult)
        assert result.status == "BREAKING"

    @pytest.mark.asyncio
    async def test_invalid_status_returns_none(self) -> None:
        pm = MagicMock()
        pm.generate = AsyncMock(
            return_value=SimpleNamespace(
                content='{"status":"UNKNOWN","confidence":0.5,"reason":"r","meaningful_update":false}',
                text="",
            )
        )
        result = await run_llm_story_activity_check(
            activity=_activity(), cluster=_cluster(), provider_manager=pm
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self) -> None:
        pm = MagicMock()
        pm.generate = AsyncMock(side_effect=RuntimeError("boom"))
        result = await run_llm_story_activity_check(
            activity=_activity(), cluster=_cluster(), provider_manager=pm
        )
        assert result is None


__all__ = ["TestRunLLMStoryActivityCheck"]
