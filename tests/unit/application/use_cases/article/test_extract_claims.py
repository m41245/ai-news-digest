"""
Unit tests for ExtractClaimsUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.use_cases.article.extract_claims import (
    ExtractClaimsUseCase,
)
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.domain.models.article import Article


def _article(content: str = "Some content", summary: str = "Summary") -> Article:
    return Article.create(
        title="Title",
        url="https://example.com",
        summary=summary,
        content=content,
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )


def _response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.provider = "openai"
    resp.model = "gpt"
    return resp


class TestExtractClaimsUseCase:
    @pytest.mark.asyncio
    async def test_empty_content_returns_empty(self) -> None:
        article = Article.create(
            title="",
            url="https://example.com",
            summary="",
            content=None,
            source_id=uuid4(),
            published_at=datetime.now(UTC),
        )
        use_case = ExtractClaimsUseCase(provider_manager=MagicMock(), claim_repository=AsyncMock())
        result = await use_case.execute(article, uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_provider_failure_raises(self) -> None:
        pm = MagicMock()
        pm.generate = AsyncMock(side_effect=RuntimeError("boom"))
        repo = AsyncMock()
        use_case = ExtractClaimsUseCase(provider_manager=pm, claim_repository=repo)
        with pytest.raises(ExternalServiceError):
            await use_case.execute(_article(), uuid4())

    @pytest.mark.asyncio
    async def test_invalid_json_raises(self) -> None:
        pm = MagicMock()
        pm.generate = AsyncMock(return_value=_response("not json"))
        repo = AsyncMock()
        use_case = ExtractClaimsUseCase(provider_manager=pm, claim_repository=repo)
        with pytest.raises(ExternalServiceError):
            await use_case.execute(_article(), uuid4())

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty(self) -> None:
        pm = MagicMock()
        pm.generate = AsyncMock(return_value=_response(""))
        repo = AsyncMock()
        use_case = ExtractClaimsUseCase(provider_manager=pm, claim_repository=repo)
        result = await use_case.execute(_article(), uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_non_dict_returns_empty(self) -> None:
        pm = MagicMock()
        pm.generate = AsyncMock(return_value=_response("[1,2,3]"))
        repo = AsyncMock()
        use_case = ExtractClaimsUseCase(provider_manager=pm, claim_repository=repo)
        result = await use_case.execute(_article(), uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_valid_claims_materialized(self) -> None:
        content = '{"claims": [{"claim": "X happened", "type": "FACT", "confidence": 0.9, "evidence": [{"evidence_type": "ARTICLE_TEXT", "excerpt": "excerpt", "source_location": "loc"}]}]}'
        pm = MagicMock()
        pm.generate = AsyncMock(return_value=_response(content))
        repo = AsyncMock()
        use_case = ExtractClaimsUseCase(provider_manager=pm, claim_repository=repo)
        result = await use_case.execute(_article(), uuid4())
        assert len(result) == 1
        assert result[0].claim_text == "X happened"
        repo.delete_claims_for_article.assert_awaited()

    @pytest.mark.asyncio
    async def test_invalid_claim_skipped(self) -> None:
        content = '{"claims": [{"claim": "", "type": "FACT"}]}'
        pm = MagicMock()
        pm.generate = AsyncMock(return_value=_response(content))
        repo = AsyncMock()
        use_case = ExtractClaimsUseCase(provider_manager=pm, claim_repository=repo)
        result = await use_case.execute(_article(), uuid4())
        assert result == []


__all__ = ["TestExtractClaimsUseCase"]
