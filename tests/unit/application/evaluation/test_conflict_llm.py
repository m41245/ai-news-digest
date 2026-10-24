"""
Unit tests for LLM conflict analysis helpers.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.evaluation.conflict_llm import (
    LLMConflictOutput,
    run_llm_conflict_analysis,
)
from ai_news_digest.domain.enums.claim_type import ClaimType
from ai_news_digest.domain.models.claim import Claim


class TestLLMConflictOutput:
    def test_valid_conflict(self) -> None:
        result = LLMConflictOutput(
            relationship="conflict",
            confidence=0.9,
            reason="values differ",
            conflicting_aspects=["differing_value", "unknown"],
        )
        assert result.relationship == "CONFLICT"
        assert result.confidence == 0.9
        assert result.conflicting_aspects == ["differing_value"]

    def test_invalid_relationship_raises(self) -> None:
        with pytest.raises(ValueError):
            LLMConflictOutput(relationship="MAYBE", confidence=0.5, reason="x")


class TestRunLLMConflictAnalysis:
    def _candidate(self) -> SimpleNamespace:
        claim_a = Claim.create(
            article_id=uuid4(), source_id=uuid4(), claim_text="A", claim_type=ClaimType.OTHER
        )
        claim_b = Claim.create(
            article_id=uuid4(), source_id=uuid4(), claim_text="B", claim_type=ClaimType.OTHER
        )
        return SimpleNamespace(claim_a=claim_a, claim_b=claim_b)

    @pytest.mark.asyncio
    async def test_empty_content_returns_none(self) -> None:
        candidate = self._candidate()
        pm = MagicMock()
        pm.generate = AsyncMock(return_value=SimpleNamespace(content="", text=""))
        result = await run_llm_conflict_analysis(
            candidate=candidate, provider_manager=pm, deterministic=None
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_json_returns_none(self) -> None:
        candidate = self._candidate()
        pm = MagicMock()
        pm.generate = AsyncMock(return_value=SimpleNamespace(content="not json", text=""))
        result = await run_llm_conflict_analysis(
            candidate=candidate, provider_manager=pm, deterministic=None
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_conflict_returns_result(self) -> None:
        candidate = self._candidate()
        pm = MagicMock()
        pm.generate = AsyncMock(
            return_value=SimpleNamespace(
                content='{"relationship":"CONFLICT","confidence":0.9,"reason":"r","conflicting_aspects":["differing_value"]}',
                text="",
            )
        )
        result = await run_llm_conflict_analysis(
            candidate=candidate, provider_manager=pm, deterministic=None
        )
        assert result is not None
        assert result.relationship == "CONFLICT"

    @pytest.mark.asyncio
    async def test_uncertain_returns_none(self) -> None:
        candidate = self._candidate()
        pm = MagicMock()
        pm.generate = AsyncMock(
            return_value=SimpleNamespace(
                content='{"relationship":"UNCERTAIN","confidence":0.5,"reason":"r"}', text=""
            )
        )
        result = await run_llm_conflict_analysis(
            candidate=candidate, provider_manager=pm, deterministic=None
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_no_conflict_returns_none(self) -> None:
        candidate = self._candidate()
        pm = MagicMock()
        pm.generate = AsyncMock(
            return_value=SimpleNamespace(
                content='{"relationship":"NO_CONFLICT","confidence":0.5,"reason":"r"}', text=""
            )
        )
        result = await run_llm_conflict_analysis(
            candidate=candidate, provider_manager=pm, deterministic=None
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self) -> None:
        candidate = self._candidate()
        pm = MagicMock()
        pm.generate = AsyncMock(side_effect=RuntimeError("boom"))
        result = await run_llm_conflict_analysis(
            candidate=candidate, provider_manager=pm, deterministic=None
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_deterministic_note_branch(self) -> None:
        candidate = self._candidate()
        deterministic = SimpleNamespace(
            conflict_type=SimpleNamespace(value="VALUE"), explanation="exp"
        )
        pm = MagicMock()
        pm.generate = AsyncMock(return_value=SimpleNamespace(content="", text=""))
        result = await run_llm_conflict_analysis(
            candidate=candidate, provider_manager=pm, deterministic=deterministic
        )
        assert result is None


__all__ = ["TestLLMConflictOutput", "TestRunLLMConflictAnalysis"]
