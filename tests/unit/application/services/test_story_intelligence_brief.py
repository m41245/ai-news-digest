"""
Unit tests for the M95 StoryIntelligenceBriefService assembly logic.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.services.story_intelligence_brief import (
    StoryIntelligenceBriefService,
)
from ai_news_digest.domain.enums.conflict_status import ConflictStatus
from ai_news_digest.domain.enums.conflict_type import ConflictType
from ai_news_digest.domain.evaluation.quality_gates import (
    IntelligenceComponent,
    QualityGateResultDetail,
)
from ai_news_digest.domain.models.conflict import Conflict


def _make_article(
    article_id: uuid4,
    cluster_id: uuid4,
    source_id: uuid4,
    published_at: datetime,
    title: str = "Test Article",
    summary: str | None = "Test summary",
    key_takeaways: tuple[str, ...] = (),
    why_it_matters: str | None = None,
    companies: tuple[str, ...] = (),
    topics: tuple[str, ...] = (),
    ai_provider: str | None = None,
    ai_model: str | None = None,
) -> Any:
    article = MagicMock()
    article.id = article_id
    article.title = title
    article.url = f"https://example.com/article/{article_id}"
    article.summary = summary
    article.published_at = published_at
    article.source_id = source_id
    article.cluster_id = cluster_id
    article.importance_score = 0.7
    article.confidence = 0.8
    article.key_takeaways = list(key_takeaways)
    article.why_it_matters = why_it_matters
    article.companies = list(companies)
    article.topics = list(topics)
    article.ai_provider = ai_provider
    article.ai_model = ai_model
    return article


def _make_source(source_id: uuid4, name: str, source_type: str = "tech_publication") -> Any:
    source = MagicMock()
    source.id = source_id
    source.name = name
    source.source_type = MagicMock()
    source.source_type.value = source_type
    return source


def _make_cluster(cluster_id: uuid4, slug: str, title: str = "Test Story") -> Any:
    cluster = MagicMock()
    cluster.id = cluster_id
    cluster.slug = slug
    cluster.title = title
    cluster.summary = "Test summary"
    cluster.status = MagicMock()
    cluster.status.value = "ACTIVE"
    cluster.first_published_at = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)
    cluster.last_updated_at = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    cluster.importance_score = 0.8
    cluster.confidence = 0.9
    cluster.ranking_score = 0.85
    cluster.ranking_explanation = "High trust sources"
    cluster.representative_article_id = None
    return cluster


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    container.story_cluster_repository = AsyncMock()
    container.article_repository = AsyncMock()
    container.source_repository = AsyncMock()
    container.claim_repository = AsyncMock()
    container.conflict_repository = AsyncMock()
    container.story_activity_repository = AsyncMock()
    container.trend_repository = AsyncMock()
    container.relationship_repository = AsyncMock()
    container.company_repository = AsyncMock()
    container.topic_repository = AsyncMock()
    container.related_story_finder = MagicMock()
    container.quality_gate_repository = AsyncMock()
    return container


class TestStoryIntelligenceBriefService:
    async def test_build_brief_returns_complete_brief(
        self,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        source_id = uuid4()
        article_id = uuid4()
        now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

        cluster = _make_cluster(cluster_id, "test-story", "Test Story")
        source = _make_source(source_id, "Tech Daily", "tech_publication")
        article = _make_article(
            article_id=article_id,
            cluster_id=cluster_id,
            source_id=source_id,
            published_at=now,
            title="Test Article",
            summary="Test summary",
            key_takeaways=("Key takeaway 1",),
            why_it_matters="This matters because of AI",
            companies=("OpenAI",),
            topics=("AI",),
        )

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = [article]
        mock_container.source_repository.list_all.return_value = [source]
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        service = StoryIntelligenceBriefService(container=mock_container)
        brief = await service.build_brief(slug="test-story")

        assert brief["id"] == str(cluster_id)
        assert brief["title"] == "Test Story"
        assert brief["slug"] == "test-story"
        assert brief["status"] == "ACTIVE"
        assert brief["article_count"] == 1
        assert brief["source_count"] == 1
        assert brief["summary"] == "Test summary"
        assert "Key takeaway 1" in brief["key_takeaways"]
        assert brief["why_it_matters"] == "This matters because of AI"
        assert brief["entities"]["companies"] == []

    async def test_build_brief_returns_empty_for_missing_cluster(
        self,
        mock_container: MagicMock,
    ) -> None:
        mock_container.story_cluster_repository.get_by_slug.return_value = None
        service = StoryIntelligenceBriefService(container=mock_container)
        brief = await service.build_brief(slug="nonexistent")
        assert brief == {}

    async def test_build_brief_handles_claim_extraction(
        self,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        source_id = uuid4()
        article_id = uuid4()
        now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

        cluster = _make_cluster(cluster_id, "test-story")
        source = _make_source(source_id, "Tech Daily")
        article = _make_article(
            article_id=article_id,
            cluster_id=cluster_id,
            source_id=source_id,
            published_at=now,
        )

        from ai_news_digest.domain.models.evidence import EvidenceAnchor

        claim = MagicMock()
        claim.id = uuid4()
        claim.article_id = article_id
        claim.source_id = source_id
        claim.claim_text = "AI model improved performance"
        claim.claim_type = MagicMock()
        claim.claim_type.value = "performance"
        claim.status = MagicMock()
        claim.status.value = "SUPPORTED"
        claim.confidence = 0.9
        claim.evidence_support_score = 0.8
        claim.ai_provider = None
        claim.ai_model = None

        evidence = MagicMock()
        evidence.id = uuid4()
        evidence.claim_id = claim.id
        evidence.article_id = article_id
        evidence.evidence_type = MagicMock()
        evidence.evidence_type.value = "quote"
        evidence.excerpt = "Performance improved by 30%"
        evidence.source_location = "paragraph 2"
        evidence.strength = MagicMock()
        evidence.strength.value = "strong"
        evidence.anchor = EvidenceAnchor(
            sentence_index=0,
            paragraph_index=0,
            character_start=0,
            character_end=10,
            content_hash="abc",
        )

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = [article]
        mock_container.source_repository.list_all.return_value = [source]
        mock_container.claim_repository.list_by_article_id.return_value = [claim]
        mock_container.claim_repository.list_evidence_by_claim_id.return_value = [evidence]
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        service = StoryIntelligenceBriefService(container=mock_container)
        brief = await service.build_brief(slug="test-story")

        assert len(brief["claims"]) == 1
        assert brief["claims"][0]["claim_text"] == "AI model improved performance"
        assert brief["claims"][0]["status"] == "SUPPORTED"
        assert brief["claims"][0]["evidence_count"] == 1
        assert brief["claims"][0]["evidence"] is not None
        assert brief["claims"][0]["evidence"][0]["excerpt"] == "Performance improved by 30%"

    async def test_build_brief_deduplicates_claims(
        self,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        source_id = uuid4()
        article_id_a = uuid4()
        article_id_b = uuid4()
        now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

        cluster = _make_cluster(cluster_id, "test-story")
        source = _make_source(source_id, "Tech Daily")
        article_a = _make_article(
            article_id=article_id_a,
            cluster_id=cluster_id,
            source_id=source_id,
            published_at=now,
        )
        article_b = _make_article(
            article_id=article_id_b,
            cluster_id=cluster_id,
            source_id=source_id,
            published_at=now,
        )

        claim = MagicMock()
        claim.id = uuid4()
        claim.article_id = article_id_a
        claim.source_id = source_id
        claim.claim_text = "Same claim"
        claim.claim_type = MagicMock()
        claim.claim_type.value = "fact"
        claim.status = MagicMock()
        claim.status.value = "SUPPORTED"
        claim.confidence = 0.9
        claim.evidence_support_score = 0.8
        claim.ai_provider = None
        claim.ai_model = None

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = [article_a, article_b]
        mock_container.source_repository.list_all.return_value = [source]
        mock_container.claim_repository.list_by_article_id.side_effect = [
            [claim],
            [claim],
        ]
        mock_container.claim_repository.list_evidence_by_claim_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        service = StoryIntelligenceBriefService(container=mock_container)
        brief = await service.build_brief(slug="test-story")

        assert len(brief["claims"]) == 1
        assert brief["claims"][0]["claim_text"] == "Same claim"

    async def test_build_brief_handles_empty_articles(
        self,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        cluster = _make_cluster(cluster_id, "empty-story")
        cluster.summary = None

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = []
        mock_container.source_repository.list_all.return_value = []
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        service = StoryIntelligenceBriefService(container=mock_container)
        brief = await service.build_brief(slug="empty-story")

        assert brief["id"] == str(cluster_id)
        assert brief["article_count"] == 0
        assert brief["source_count"] == 0
        assert brief["claims"] == []
        assert brief["conflicts"] == []

    async def test_build_brief_handles_conflicts(
        self,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        source_a_id = uuid4()
        source_b_id = uuid4()
        article_a_id = uuid4()
        article_b_id = uuid4()
        now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

        cluster = _make_cluster(cluster_id, "conflict-story")
        source_a = _make_source(source_a_id, "Source A", "tech_publication")
        source_b = _make_source(source_b_id, "Source B", "business_news")
        article_a = _make_article(
            article_id=article_a_id,
            cluster_id=cluster_id,
            source_id=source_a_id,
            published_at=now,
            title="Article A",
        )
        article_b = _make_article(
            article_id=article_b_id,
            cluster_id=cluster_id,
            source_id=source_b_id,
            published_at=now,
            title="Article B",
        )

        conflict = Conflict(
            id=uuid4(),
            claim_a_id=uuid4(),
            claim_b_id=uuid4(),
            article_a_id=article_a_id,
            article_b_id=article_b_id,
            source_a_id=source_a_id,
            source_b_id=source_b_id,
            conflict_type=ConflictType.OTHER,
            status=ConflictStatus.CONFIRMED,
            confidence=0.8,
            explanation="Sources disagree",
            detection_version="v1",
            story_cluster_id=cluster_id,
            same_source=False,
        )

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = [article_a, article_b]
        mock_container.source_repository.list_all.return_value = [source_a, source_b]
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = [conflict]
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        service = StoryIntelligenceBriefService(container=mock_container)
        brief = await service.build_brief(slug="conflict-story")

        assert len(brief["conflicts"]) == 1
        assert brief["conflicts"][0]["explanation"] == "Sources disagree"
        assert brief["quality"]["conflict_count"] == 1
        assert "conflicting_evidence" in brief["quality"]["quality_flags"]

    async def test_build_brief_degraded_single_source(
        self,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        source_id = uuid4()
        article_id = uuid4()
        now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

        cluster = _make_cluster(cluster_id, "degraded-story")
        source = _make_source(source_id, "Tech Daily")
        article = _make_article(
            article_id=article_id,
            cluster_id=cluster_id,
            source_id=source_id,
            published_at=now,
        )

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = [article]
        mock_container.source_repository.list_all.return_value = [source]
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        service = StoryIntelligenceBriefService(container=mock_container)
        brief = await service.build_brief(slug="degraded-story")

        assert brief["quality"]["health_status"] == "degraded"
        assert brief["quality"]["degraded"] is True
        assert "single_source" in brief["quality"]["quality_flags"]

    async def test_build_brief_blocked_by_quality_gate(
        self,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        source_id = uuid4()
        article_id = uuid4()
        now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

        cluster = _make_cluster(cluster_id, "blocked-story")
        source = _make_source(source_id, "Tech Daily")
        article = _make_article(
            article_id=article_id,
            cluster_id=cluster_id,
            source_id=source_id,
            published_at=now,
        )

        fail_result = QualityGateResultDetail(
            gate_id="story-clustering-success",
            component=IntelligenceComponent.STORY_CLUSTERING,
            metric_type="story_clustering_success_rate",
            result="fail",
            current_value=0.5,
            threshold=0.8,
            operator="gte",
            sample_count=10,
            min_sample_size=5,
            severity="warning",
            explanation="Story clustering success rate below threshold",
            evaluated_at=now,
        )

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = [article]
        mock_container.source_repository.list_all.return_value = [source]
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)
        mock_container.quality_gate_repository.list_results.return_value = ([fail_result], 1)

        service = StoryIntelligenceBriefService(container=mock_container)
        brief = await service.build_brief(slug="blocked-story")

        assert brief["quality"]["health_status"] == "blocked"
        assert "quality_gate_blocked" in brief["quality"]["quality_flags"]

    async def test_build_brief_ai_disabled_fallback(
        self,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()

        cluster = _make_cluster(cluster_id, "ai-disabled-story")
        cluster.summary = None

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = []
        mock_container.source_repository.list_all.return_value = []
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        service = StoryIntelligenceBriefService(container=mock_container)
        brief = await service.build_brief(slug="ai-disabled-story")

        assert brief["summary"] is None
        assert brief["key_takeaways"] == []
        assert brief["why_it_matters"] is None
        assert brief["claims"] == []
        assert brief["conflicts"] == []
        assert brief["timeline"] == []
        assert brief["quality"]["health_status"] == "insufficient_data"

    async def test_build_brief_bounds_enforcement(
        self,
        mock_container: MagicMock,
    ) -> None:
        cluster_id = uuid4()
        source_id = uuid4()
        now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

        cluster = _make_cluster(cluster_id, "bounds-story")
        source = _make_source(source_id, "Tech Daily")

        articles = []
        for i in range(30):
            article = _make_article(
                article_id=uuid4(),
                cluster_id=cluster_id,
                source_id=source_id,
                published_at=now,
                title=f"Article {i}",
                key_takeaways=(f"Takeaway {i}",),
            )
            articles.append(article)

        mock_container.story_cluster_repository.get_by_slug.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = articles
        mock_container.source_repository.list_all.return_value = [source]
        mock_container.claim_repository.list_by_article_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        mock_container.story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_container.trend_repository.list_public.return_value = []
        mock_container.relationship_repository.list_for_entity.return_value = []
        mock_container.company_repository.list_by_ids.return_value = []
        mock_container.topic_repository.list_by_ids.return_value = []
        mock_container.related_story_finder.find_for_article.return_value = []
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)
        mock_container.quality_gate_repository.list_results.return_value = ([], 0)

        service = StoryIntelligenceBriefService(container=mock_container)
        brief = await service.build_brief(slug="bounds-story")

        assert len(brief["key_takeaways"]) <= 8
        assert len(brief["sources"]) <= 20
        for src in brief["sources"]:
            assert len(src.get("articles", [])) <= 5
        assert len(brief["timeline"]) <= 30


__all__ = ["TestStoryIntelligenceBriefService"]
