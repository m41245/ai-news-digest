"""
Tests for story intelligence utilities: timeline, source-role classification,
and what-changed detection.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ai_news_digest.application.use_cases.story_cluster.story_intelligence import (
    TimelineItem,
    build_timeline,
    classify_source_role,
    compute_what_changed,
    compute_what_changed_with_evidence,
    detect_signals,
)


def _make_article(
    title: str = "Test Article",
    url: str = "https://example.com/article",
    published_at: datetime | None = None,
    source_id=None,
    importance_score: float | None = None,
    confidence: float | None = None,
    key_takeaways: tuple[str, ...] = (),
    companies: tuple[str, ...] = (),
    topics: tuple[str, ...] = (),
    summary: str = "Test summary",
):
    if source_id is None:
        source_id = uuid4()
    if published_at is None:
        published_at = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

    class FakeArticle:
        def __init__(self):
            self.id = uuid4()
            self.title = title
            self.url = url
            self.summary = summary
            self.published_at = published_at
            self.source_id = source_id
            self.importance_score = importance_score
            self.confidence = confidence
            self.key_takeaways = key_takeaways
            self.companies = companies
            self.topics = topics

    return FakeArticle()


class TestClassifySourceRole:
    """Tests for conservative source-role classification."""

    def test_official_company_same_day_returns_primary_announcement(self):
        cluster_first = datetime(2026, 9, 4, 8, 0, tzinfo=UTC)
        article_published = datetime(2026, 9, 4, 10, 0, tzinfo=UTC)
        role = classify_source_role(
            article_published_at=article_published,
            cluster_first_published_at=cluster_first,
            source_type="official_company",
        )
        assert role == "Primary announcement"

    def test_official_company_beyond_seven_days_returns_related_coverage(self):
        cluster_first = datetime(2026, 9, 4, 8, 0, tzinfo=UTC)
        article_published = datetime(2026, 9, 15, 10, 0, tzinfo=UTC)
        role = classify_source_role(
            article_published_at=article_published,
            cluster_first_published_at=cluster_first,
            source_type="official_company",
        )
        assert role == "Related coverage"

    def test_research_org_within_seven_days_returns_technical_analysis(self):
        cluster_first = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)
        article_published = datetime(2026, 9, 4, 10, 0, tzinfo=UTC)
        role = classify_source_role(
            article_published_at=article_published,
            cluster_first_published_at=cluster_first,
            source_type="research_org",
        )
        assert role == "Technical analysis"

    def test_tech_publication_same_day_returns_independent_reporting(self):
        cluster_first = datetime(2026, 9, 4, 8, 0, tzinfo=UTC)
        article_published = datetime(2026, 9, 4, 14, 0, tzinfo=UTC)
        role = classify_source_role(
            article_published_at=article_published,
            cluster_first_published_at=cluster_first,
            source_type="tech_publication",
        )
        assert role == "Independent reporting"

    def test_business_news_same_day_returns_independent_reporting(self):
        cluster_first = datetime(2026, 9, 4, 8, 0, tzinfo=UTC)
        article_published = datetime(2026, 9, 4, 14, 0, tzinfo=UTC)
        role = classify_source_role(
            article_published_at=article_published,
            cluster_first_published_at=cluster_first,
            source_type="business_news",
        )
        assert role == "Independent reporting"

    def test_follow_up_within_seven_days(self):
        cluster_first = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)
        article_published = datetime(2026, 9, 3, 10, 0, tzinfo=UTC)
        role = classify_source_role(
            article_published_at=article_published,
            cluster_first_published_at=cluster_first,
            source_type="other",
        )
        assert role == "Follow-up"

    def test_reaction_beyond_seven_days(self):
        cluster_first = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)
        article_published = datetime(2026, 9, 10, 10, 0, tzinfo=UTC)
        role = classify_source_role(
            article_published_at=article_published,
            cluster_first_published_at=cluster_first,
            source_type="other",
        )
        assert role == "Related coverage"

    def test_correction_detected_by_title(self):
        cluster_first = datetime(2026, 9, 4, 8, 0, tzinfo=UTC)
        article_published = datetime(2026, 9, 4, 10, 0, tzinfo=UTC)
        role = classify_source_role(
            article_published_at=article_published,
            cluster_first_published_at=cluster_first,
            source_type="other",
            article_title="Correction: earlier report contained errors",
        )
        assert role == "Correction"

    def test_background_detected_by_title(self):
        cluster_first = datetime(2026, 9, 4, 8, 0, tzinfo=UTC)
        article_published = datetime(2026, 9, 4, 10, 0, tzinfo=UTC)
        role = classify_source_role(
            article_published_at=article_published,
            cluster_first_published_at=cluster_first,
            source_type="other",
            article_title="Background: what you need to know about this event",
        )
        assert role == "Background"

    def test_unknown_source_type_beyond_seven_days_returns_related_coverage(self):
        cluster_first = datetime(2026, 9, 4, 8, 0, tzinfo=UTC)
        article_published = datetime(2026, 9, 15, 10, 0, tzinfo=UTC)
        role = classify_source_role(
            article_published_at=article_published,
            cluster_first_published_at=cluster_first,
            source_type="unknown_type",
        )
        assert role == "Related coverage"

    def test_none_source_type_falls_back(self):
        cluster_first = datetime(2026, 9, 4, 8, 0, tzinfo=UTC)
        article_published = datetime(2026, 9, 4, 10, 0, tzinfo=UTC)
        role = classify_source_role(
            article_published_at=article_published,
            cluster_first_published_at=cluster_first,
            source_type=None,
        )
        assert role == "Independent reporting"

    def test_fallback_when_confidence_is_low(self):
        cluster_first = datetime(2026, 9, 4, 8, 0, tzinfo=UTC)
        article_published = datetime(2026, 9, 15, 10, 0, tzinfo=UTC)
        role = classify_source_role(
            article_published_at=article_published,
            cluster_first_published_at=cluster_first,
            source_type="other",
        )
        assert role == "Related coverage"


class TestBuildTimeline:
    """Tests for chronological timeline construction."""

    def test_articles_ordered_oldest_first(self):
        articles = [
            _make_article(title="Latest", published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC)),
            _make_article(title="Earliest", published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC)),
            _make_article(title="Middle", published_at=datetime(2026, 9, 2, 10, 0, tzinfo=UTC)),
        ]
        source_map = {a.source_id: "Test Source" for a in articles}
        timeline = build_timeline(articles, source_map)
        assert timeline[0]["title"] == "Earliest"
        assert timeline[1]["title"] == "Middle"
        assert timeline[2]["title"] == "Latest"

    def test_single_article_timeline(self):
        articles = [
            _make_article(title="Only one", published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC)),
        ]
        source_map = {articles[0].source_id: "Test Source"}
        timeline = build_timeline(articles, source_map)
        assert len(timeline) == 1
        assert timeline[0]["title"] == "Only one"

    def test_empty_articles_returns_empty_timeline(self):
        timeline = build_timeline([], {})
        assert timeline == []

    def test_timeline_includes_source_name(self):
        article = _make_article(published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC))
        source_map = {article.source_id: "The Tech Daily"}
        timeline = build_timeline([article], source_map)
        assert timeline[0]["source_name"] == "The Tech Daily"

    def test_timeline_preserves_article_url(self):
        article = _make_article(
            url="https://example.com/ai-news",
            published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
        )
        source_map = {article.source_id: "Test Source"}
        timeline = build_timeline([article], source_map)
        assert timeline[0]["url"] == "https://example.com/ai-news"

    def test_timeline_preserves_article_title(self):
        article = _make_article(
            title="AI Breakthrough",
            published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
        )
        source_map = {article.source_id: "Test Source"}
        timeline = build_timeline([article], source_map)
        assert timeline[0]["title"] == "AI Breakthrough"

    def test_timeline_with_single_article_no_date_sorting(self):
        article = _make_article(published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC))
        source_map = {article.source_id: "Test Source"}
        timeline = build_timeline([article], source_map)
        assert len(timeline) == 1
        assert timeline[0]["published_at"] == "2026-09-04T12:00:00+00:00"


class TestComputeWhatChanged:
    """Tests for what-changed detection."""

    def test_single_article_returns_empty(self):
        timeline = [
            {
                "id": "1",
                "title": "Article 1",
                "url": "https://example.com/1",
                "published_at": "2026-09-04T12:00:00+00:00",
                "source_name": "Source A",
                "importance_score": 0.8,
                "confidence": 0.9,
                "key_takeaways": ["Takeaway 1"],
                "companies": ["OpenAI"],
                "topics": ["AI"],
            }
        ]
        changes = compute_what_changed(timeline)
        assert changes == []

    def test_empty_timeline_returns_empty(self):
        changes = compute_what_changed([])
        assert changes == []

    def test_detects_title_change(self):
        timeline = [
            {
                "id": "1",
                "title": "Original headline",
                "url": "https://example.com/1",
                "published_at": "2026-09-01T08:00:00+00:00",
                "source_name": "Source A",
                "importance_score": 0.8,
                "confidence": 0.9,
                "key_takeaways": ["Takeaway 1"],
                "companies": ["OpenAI"],
                "topics": ["AI"],
            },
            {
                "id": "2",
                "title": "Updated headline",
                "url": "https://example.com/2",
                "published_at": "2026-09-04T12:00:00+00:00",
                "source_name": "Source B",
                "importance_score": 0.8,
                "confidence": 0.9,
                "key_takeaways": ["Takeaway 1"],
                "companies": ["OpenAI"],
                "topics": ["AI"],
            },
        ]
        changes = compute_what_changed(timeline)
        assert len(changes) == 1
        assert "Updated headline" in changes[0]

    def test_detects_new_companies(self):
        timeline = [
            {
                "id": "1",
                "title": "AI News",
                "url": "https://example.com/1",
                "published_at": "2026-09-01T08:00:00+00:00",
                "source_name": "Source A",
                "importance_score": 0.8,
                "confidence": 0.9,
                "key_takeaways": ["Takeaway 1"],
                "companies": ["OpenAI"],
                "topics": ["AI"],
            },
            {
                "id": "2",
                "title": "AI News",
                "url": "https://example.com/2",
                "published_at": "2026-09-04T12:00:00+00:00",
                "source_name": "Source B",
                "importance_score": 0.8,
                "confidence": 0.9,
                "key_takeaways": ["Takeaway 1"],
                "companies": ["OpenAI", "Anthropic"],
                "topics": ["AI"],
            },
        ]
        changes = compute_what_changed(timeline)
        assert any("Anthropic" in c for c in changes)

    def test_detects_new_topics(self):
        timeline = [
            {
                "id": "1",
                "title": "AI News",
                "url": "https://example.com/1",
                "published_at": "2026-09-01T08:00:00+00:00",
                "source_name": "Source A",
                "importance_score": 0.8,
                "confidence": 0.9,
                "key_takeaways": ["Takeaway 1"],
                "companies": ["OpenAI"],
                "topics": ["AI"],
            },
            {
                "id": "2",
                "title": "AI News",
                "url": "https://example.com/2",
                "published_at": "2026-09-04T12:00:00+00:00",
                "source_name": "Source B",
                "importance_score": 0.8,
                "confidence": 0.9,
                "key_takeaways": ["Takeaway 1"],
                "companies": ["OpenAI"],
                "topics": ["AI", "robotics"],
            },
        ]
        changes = compute_what_changed(timeline)
        assert any("robotics" in c for c in changes)

    def test_detects_importance_score_change(self):
        timeline = [
            {
                "id": "1",
                "title": "AI News",
                "url": "https://example.com/1",
                "published_at": "2026-09-01T08:00:00+00:00",
                "source_name": "Source A",
                "importance_score": 0.5,
                "confidence": 0.9,
                "key_takeaways": ["Takeaway 1"],
                "companies": ["OpenAI"],
                "topics": ["AI"],
            },
            {
                "id": "2",
                "title": "AI News",
                "url": "https://example.com/2",
                "published_at": "2026-09-04T12:00:00+00:00",
                "source_name": "Source B",
                "importance_score": 0.9,
                "confidence": 0.9,
                "key_takeaways": ["Takeaway 1"],
                "companies": ["OpenAI"],
                "topics": ["AI"],
            },
        ]
        changes = compute_what_changed(timeline)
        assert any("0.5" in c and "0.9" in c for c in changes)

    def test_insufficient_evidence_returns_empty(self):
        timeline = [
            {
                "id": "1",
                "title": "Same headline",
                "url": "https://example.com/1",
                "published_at": "2026-09-01T08:00:00+00:00",
                "source_name": "Source A",
                "importance_score": 0.8,
                "confidence": 0.9,
                "key_takeaways": ["Same takeaway"],
                "companies": ["OpenAI"],
                "topics": ["AI"],
            },
            {
                "id": "2",
                "title": "Same headline",
                "url": "https://example.com/2",
                "published_at": "2026-09-04T12:00:00+00:00",
                "source_name": "Source B",
                "importance_score": 0.8,
                "confidence": 0.9,
                "key_takeaways": ["Same takeaway"],
                "companies": ["OpenAI"],
                "topics": ["AI"],
            },
        ]
        changes = compute_what_changed(timeline)
        assert changes == []

    def test_multiple_articles_accumulates_changes(self):
        timeline = [
            {
                "id": "1",
                "title": "First headline",
                "url": "https://example.com/1",
                "published_at": "2026-09-01T08:00:00+00:00",
                "source_name": "Source A",
                "importance_score": 0.5,
                "confidence": 0.9,
                "key_takeaways": ["Takeaway 1"],
                "companies": ["OpenAI"],
                "topics": ["AI"],
            },
            {
                "id": "2",
                "title": "Second headline",
                "url": "https://example.com/2",
                "published_at": "2026-09-02T08:00:00+00:00",
                "source_name": "Source B",
                "importance_score": 0.5,
                "confidence": 0.9,
                "key_takeaways": ["Takeaway 2"],
                "companies": ["OpenAI"],
                "topics": ["AI"],
            },
            {
                "id": "3",
                "title": "Third headline",
                "url": "https://example.com/3",
                "published_at": "2026-09-03T08:00:00+00:00",
                "source_name": "Source C",
                "importance_score": 0.9,
                "confidence": 0.9,
                "key_takeaways": ["Takeaway 3"],
                "companies": ["OpenAI", "Anthropic"],
                "topics": ["AI", "robotics"],
            },
        ]
        changes = compute_what_changed(timeline)
        assert len(changes) >= 3


__all__ = [
    "TestBuildTimeline",
    "TestClassifySourceRole",
    "TestComputeWhatChanged",
    "TestComputeWhatChangedWithEvidence",
    "TestDetectSignals",
]


def _timeline_item_dict(**overrides: object) -> TimelineItem:
    base: dict[str, object] = {
        "id": str(uuid4()),
        "title": "OpenAI announces new model",
        "url": "https://example.com/article",
        "summary": "OpenAI released a new model.",
        "published_at": "2026-09-04T08:00:00+00:00",
        "source_name": "Test Source",
        "source_type": "tech_publication",
        "source_role": "Independent reporting",
        "importance_score": 0.8,
        "confidence": 0.9,
        "key_takeaways": ["Improved reasoning"],
        "companies": ["OpenAI"],
        "topics": ["language-models"],
    }
    base.update(overrides)
    return TimelineItem(**base)  # type: ignore[arg-type]


class TestComputeWhatChangedWithEvidence:
    """Tests for the evidence-backed what-changed helper."""

    def test_returns_empty_for_single_article(self) -> None:
        items = [_timeline_item_dict()]
        assert compute_what_changed_with_evidence(items) == []

    def test_returns_empty_for_empty_timeline(self) -> None:
        assert compute_what_changed_with_evidence([]) == []

    def test_detects_headline_change_with_evidence(self) -> None:
        first = _timeline_item_dict(
            id="11111111-1111-1111-1111-111111111111",
            title="Original headline",
        )
        latest = _timeline_item_dict(
            id="22222222-2222-2222-2222-222222222222",
            title="Updated headline",
        )
        items = compute_what_changed_with_evidence([first, latest])
        assert len(items) == 1
        item = items[0]
        assert "Updated headline" in item.description
        assert item.detection_method == "deterministic_title_diff"
        assert item.evidence_type == "headline_change"
        assert {ref.article_id for ref in item.evidence} == {
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        }

    def test_detects_new_companies_with_evidence(self) -> None:
        first = _timeline_item_dict(companies=["OpenAI"])
        latest = _timeline_item_dict(companies=["OpenAI", "Anthropic"])
        items = compute_what_changed_with_evidence([first, latest])
        company_items = [i for i in items if i.evidence_type == "new_entities"]
        assert len(company_items) == 1
        assert "Anthropic" in company_items[0].description

    def test_detects_importance_score_change_with_evidence(self) -> None:
        first = _timeline_item_dict(
            id="33333333-3333-3333-3333-333333333333",
            importance_score=0.4,
        )
        latest = _timeline_item_dict(
            id="44444444-4444-4444-4444-444444444444",
            importance_score=0.9,
            source_name="Another Source",
        )
        items = compute_what_changed_with_evidence([first, latest])
        importance_items = [i for i in items if i.evidence_type == "importance_change"]
        assert len(importance_items) == 1
        assert "0.4" in importance_items[0].description
        assert "0.9" in importance_items[0].description
        assert importance_items[0].confidence == "high"

    def test_no_change_when_only_minor_metadata_differs(self) -> None:
        first = _timeline_item_dict()
        latest = _timeline_item_dict()
        # If all metadata is identical, the function should report nothing.
        items = compute_what_changed_with_evidence([first, latest])
        # headline_change detection requires different titles, so nothing here.
        headline_items = [i for i in items if i.evidence_type == "headline_change"]
        assert headline_items == []
        assert items == []

    def test_idempotent_with_same_inputs(self) -> None:
        first = _timeline_item_dict(id="1", title="First")
        latest = _timeline_item_dict(id="2", title="Second")
        first_run = compute_what_changed_with_evidence([first, latest])
        second_run = compute_what_changed_with_evidence([first, latest])
        assert [item.to_dict() for item in first_run] == [
            item.to_dict() for item in second_run
        ]


class TestDetectSignals:
    """Tests for lexical signal detection in article titles."""

    def test_detects_correction_signal(self) -> None:
        signals = detect_signals("Correction: earlier report was wrong")
        assert signals["is_correction"] is True
        assert signals["is_retraction"] is False

    def test_detects_retraction_signal(self) -> None:
        signals = detect_signals("Retraction: our earlier story was inaccurate")
        assert signals["is_retraction"] is True

    def test_detects_background_signal(self) -> None:
        signals = detect_signals("Background: what you need to know about X")
        assert signals["is_background"] is True

    def test_detects_reaction_signal(self) -> None:
        signals = detect_signals("Opinion: why the announcement matters")
        assert signals["is_reaction"] is True

    def test_returns_no_signals_for_plain_title(self) -> None:
        signals = detect_signals("New AI model released")
        assert all(value is False for value in signals.values())

    def test_handles_none_title(self) -> None:
        signals = detect_signals(None)
        assert all(value is False for value in signals.values())
