"""Tests for M93 IntelligenceEvaluationService."""

from __future__ import annotations
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
from ai_news_digest.application.services.intelligence_evaluation_service import (
    IntelligenceEvaluationService,
)
from ai_news_digest.domain.evaluation.metrics import (
    EvaluationMetricType,
    EvaluationReport,
    EvaluationStatus,
    MetricValue,
)


def _make_article(summary=None, key_takeaways_json=None, why_it_matters=None,
                  ai_provider="openai", ai_model="gpt-4", ai_processed_at=None,
                  content=None, extraction_method="rss", source_id=None):
    article = MagicMock()
    article.summary = summary
    article.key_takeaways_json = key_takeaways_json
    article.why_it_matters = why_it_matters
    article.ai_provider = ai_provider
    article.ai_model = ai_model
    article.ai_processed_at = ai_processed_at or datetime.now(UTC)
    article.content = content or "Some content here."
    article.extraction_method = extraction_method
    article.source_id = source_id
    return article


class TestIntelligenceEvaluationService:
    def setup_method(self):
        self.service = IntelligenceEvaluationService()

    @pytest.mark.asyncio
    async def test_evaluate_articles_empty(self):
        metrics = await self.service.evaluate_articles([])
        assert metrics == []

    @pytest.mark.asyncio
    async def test_evaluate_articles_validity(self):
        articles = [
            _make_article(summary="Summary", key_takeaways_json="[]", why_it_matters="matters"),
            _make_article(summary=None, key_takeaways_json=None, why_it_matters=None),
        ]
        metrics = await self.service.evaluate_articles(articles)
        validity = next(m for m in metrics if m.metric_type == EvaluationMetricType.STRUCTURED_OUTPUT_VALIDITY)
        assert validity.value == 0.5
        assert validity.sample_count == 2

    @pytest.mark.asyncio
    async def test_evaluate_claims_empty(self):
        metrics = await self.service.evaluate_claims([])
        assert metrics == []

    @pytest.mark.asyncio
    async def test_evaluate_claims_with_evidence(self):
        claim = MagicMock()
        claim.id = "claim-1"
        claim.status = "supported"
        claim.ai_provider = "openai"
        claim.ai_model = "gpt-4"
        evidence = [MagicMock()]
        metrics = await self.service.evaluate_claims(
            [claim],
            evidence_by_claim={"claim-1": evidence},
            conflicts_by_claim={},
        )
        attachment = next(m for m in metrics if m.metric_type == EvaluationMetricType.EVIDENCE_ATTACHMENT_RATE)
        assert attachment.value == 1.0
