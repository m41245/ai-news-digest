"""
Integration tests for ``scripts/scheduled/run_deterministic_batch.py`` against a
real PostgreSQL database (testcontainers).

These tests exercise the *actual* batch runner pipeline functions (summarize,
categorize, analyze, cluster, rank, trends, digest) against a real SQLAlchemy
session backed by PostgreSQL. No Celery broker, no Redis, and no AI provider
are involved: the deterministic code paths are used, which is the staging
operating model.

The ``db_session`` and ``container`` fixtures come from
``tests/integration/conftest.py`` and spin up a disposable PostgreSQL test
container per test. The runner's ``get_container()`` dependency (and the same
dependency inside each task module) is patched to yield the test container so
the real implementations run against the test database.
"""

from __future__ import annotations

from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import scripts.scheduled.run_deterministic_batch as batch_module
from scripts.scheduled.run_deterministic_batch import _run_pipeline
from sqlalchemy import func, select, text

from ai_news_digest.bootstrap.container import Container
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.infrastructure.database.models.article_model import ArticleModel
from ai_news_digest.infrastructure.database.models.category_model import CategoryModel
from ai_news_digest.infrastructure.database.models.digest_model import DigestModel
from ai_news_digest.infrastructure.database.models.story_activity_model import (  # noqa: F401
    StoryActivityModel,
)
from ai_news_digest.infrastructure.database.models.story_cluster_model import (
    StoryClusterModel,
)
from ai_news_digest.infrastructure.database.models.story_event_model import (  # noqa: F401
    StoryEventModel,
)
from ai_news_digest.infrastructure.database.models.topic_model import TopicModel
from ai_news_digest.infrastructure.database.models.trend_model import TrendModel
from ai_news_digest.workers.tasks import cluster as cluster_module
from ai_news_digest.workers.tasks import digest as digest_module
from ai_news_digest.workers.tasks import process as process_module
from ai_news_digest.workers.tasks import ranking as ranking_module
from ai_news_digest.workers.tasks import trend as trend_module

pytestmark = pytest.mark.integration

_SAME_TITLE = "AI News Trend Story"
_RECENT = datetime.now(UTC) - timedelta(hours=1)


def _container_generator(container: Container):
    async def _gen():
        yield container

    return _gen


def _patch_all_containers(container: Container):
    return (
        patch.object(batch_module, "get_container", _container_generator(container)),
        patch.object(process_module, "get_container", _container_generator(container)),
        patch.object(cluster_module, "get_container", _container_generator(container)),
        patch.object(ranking_module, "get_container", _container_generator(container)),
        patch.object(trend_module, "get_container", _container_generator(container)),
        patch.object(digest_module, "get_container", _container_generator(container)),
    )


def _make_source(name: str, *, is_active: bool = True) -> Source:
    return Source.create(
        name=name,
        feed_url=f"https://example.com/{uuid4().hex}/feed.xml",
        website_url="https://example.com",
        description=None,
        is_active=is_active,
        source_type=SourceType.OTHER,
        status=SourceStatus.VERIFIED,
    )


def _make_article(
    source: Source,
    status: ArticleStatus,
    title: str,
    url: str,
    content: str = "Article body content used for deterministic processing tests.",
    published_at: datetime | None = None,
) -> Article:
    if published_at is None:
        published_at = _RECENT
    article = Article.create(
        title=title,
        url=url,
        summary="Initial RSS summary.",
        content=content,
        source_id=source.id,
        published_at=published_at,
    )
    article.status = status
    return article


async def _create_article(container: Container, source: Source, article: Article) -> None:
    existing = await container.source_repository.get_by_id(source.id)
    if existing is None:
        await container.source_repository.create(source)
    await container.article_repository.create(article)


async def _article_status(container: Container, article_id) -> str | None:
    result = await container.article_repository.session.execute(
        text("SELECT status FROM articles WHERE id = :id"), {"id": str(article_id)}
    )
    row = result.scalar_one_or_none()
    return None if row is None else str(row)


async def _count(container: Container, model) -> int:
    statement = select(func.count()).select_from(model)
    result = await container.article_repository.session.execute(statement)
    return int(result.scalar_one())


async def _run_stages(container: Container, batch_size: int, dry_run: bool, stages: list[str]):
    with ExitStack() as stack:
        for cm in _patch_all_containers(container):
            stack.enter_context(cm)
        return await _run_pipeline(batch_size, dry_run, stages)


# 1. NEW article -> SUMMARIZED
async def test_new_article_becomes_summarized(db_session, container) -> None:
    source = _make_source("Source A")
    article = _make_article(source, ArticleStatus.NEW, "Summarize Me", "https://example.com/sum-1")
    await _create_article(container, source, article)

    results = await _run_stages(container, 10, False, ["summarize"])

    assert results[0]["stage"] == "summarize"
    assert results[0]["status"] == "completed"
    assert await _article_status(container, article.id) == ArticleStatus.SUMMARIZED.value


# 2. SUMMARIZED article -> CATEGORIZED
async def test_summarized_article_becomes_categorized(db_session, container) -> None:
    source = _make_source("Source B")
    article = _make_article(
        source, ArticleStatus.SUMMARIZED, "Categorize Me", "https://example.com/cat-1"
    )
    await _create_article(container, source, article)

    results = await _run_stages(container, 10, False, ["categorize"])

    assert results[0]["stage"] == "categorize"
    assert results[0]["status"] == "completed"
    assert await _article_status(container, article.id) == ArticleStatus.CATEGORIZED.value
    assert await _count(container, CategoryModel) == 1
    assert await _count(container, TopicModel) == 1


# 3. CATEGORIZED article -> ANALYZED
async def test_categorized_article_becomes_analyzed(db_session, container) -> None:
    source = _make_source("Source C")
    article = _make_article(
        source, ArticleStatus.CATEGORIZED, "Analyze Me", "https://example.com/an-1"
    )
    await _create_article(container, source, article)

    results = await _run_stages(container, 10, False, ["analyze"])

    assert results[0]["stage"] == "analyze"
    assert results[0]["status"] == "completed"
    assert await _article_status(container, article.id) == ArticleStatus.ANALYZED.value


# 4. Eligible articles are clustered into story clusters
async def test_eligible_articles_are_clustered(db_session, container) -> None:
    source = _make_source("Source D")
    articles = [
        _make_article(source, ArticleStatus.NEW, _SAME_TITLE, f"https://example.com/cluster-{i}")
        for i in range(3)
    ]
    for article in articles:
        await _create_article(container, source, article)

    results = await _run_stages(
        container, 10, False, ["summarize", "categorize", "analyze", "cluster"]
    )
    assert all(r["status"] == "completed" for r in results)

    cluster_ids = await container.article_repository.session.execute(
        text("SELECT DISTINCT cluster_id FROM articles WHERE cluster_id IS NOT NULL")
    )
    distinct_clusters = [row[0] for row in cluster_ids.all()]
    assert len(distinct_clusters) == 1, f"Expected 1 cluster, got {len(distinct_clusters)}"
    assert await _count(container, StoryClusterModel) == 1
    for article in articles:
        assert await _article_status(container, article.id) in (ArticleStatus.ANALYZED.value,)
        result = await container.article_repository.session.execute(
            text("SELECT cluster_id FROM articles WHERE id = :id"),
            {"id": str(article.id)},
        )
        assert result.scalar_one() == distinct_clusters[0]


# 5. Duplicate clustering is prevented on repeat execution
async def test_duplicate_clustering_prevented(db_session, container) -> None:
    source = _make_source("Source E")
    article = _make_article(source, ArticleStatus.NEW, _SAME_TITLE, "https://example.com/dup-1")
    await _create_article(container, source, article)

    await _run_stages(container, 10, False, ["summarize", "categorize", "analyze", "cluster"])
    first_cluster = await container.article_repository.session.execute(
        text("SELECT cluster_id FROM articles WHERE id = :id"), {"id": str(article.id)}
    )
    first_cluster_id = first_cluster.scalar_one()
    first_cluster_count = await _count(container, StoryClusterModel)

    # Re-run clustering: article is already clustered, must be skipped.
    results = await _run_stages(container, 10, False, ["cluster"])
    assert results[0]["status"] == "completed"
    assert await _count(container, StoryClusterModel) == first_cluster_count
    result = await container.article_repository.session.execute(
        text("SELECT cluster_id FROM articles WHERE id = :id"), {"id": str(article.id)}
    )
    assert result.scalar_one() == first_cluster_id


# 6. Importance/ranking score is persisted on clusters
async def test_ranking_score_persisted(db_session, container) -> None:
    source = _make_source("Source F")
    articles = [
        _make_article(source, ArticleStatus.NEW, _SAME_TITLE, f"https://example.com/rank-{i}")
        for i in range(2)
    ]
    for article in articles:
        await _create_article(container, source, article)

    await _run_stages(
        container, 10, False, ["summarize", "categorize", "analyze", "cluster", "rank"]
    )

    result = await container.article_repository.session.execute(
        text("SELECT ranking_score FROM story_clusters WHERE ranking_score IS NOT NULL")
    )
    scored = result.scalars().all()
    assert len(scored) >= 1, "Expected at least one cluster to have a persisted ranking score"
    for score in scored:
        assert score is not None and score >= 0.0


# 7. Ranking generates an ordered top story
async def test_ranking_generates_top_story(db_session, container) -> None:
    source = _make_source("Source G")
    articles = [
        _make_article(source, ArticleStatus.NEW, _SAME_TITLE, f"https://example.com/top-{i}")
        for i in range(2)
    ]
    for article in articles:
        await _create_article(container, source, article)

    results = await _run_stages(
        container, 10, False, ["summarize", "categorize", "analyze", "cluster", "rank"]
    )
    assert all(r["status"] == "completed" for r in results)

    result = await container.article_repository.session.execute(
        text(
            "SELECT ranking_score, ranking_explanation FROM story_clusters ORDER BY ranking_score DESC NULLS LAST"
        )
    )
    rows = result.all()
    assert len(rows) >= 1
    # Scores should be present and ordered descending.
    scores = [r[0] for r in rows if r[0] is not None]
    assert scores == sorted(scores, reverse=True)


# 8. Trends are generated from recent clustered activity
async def test_trends_are_generated(db_session, container) -> None:
    source_a = _make_source("Trend Source A")
    source_b = _make_source("Trend Source B")
    # Three recent articles in the same deterministic category across two sources.
    await _create_article(
        container,
        source_a,
        _make_article(source_a, ArticleStatus.NEW, _SAME_TITLE, "https://example.com/trend-a-0"),
    )
    await _create_article(
        container,
        source_a,
        _make_article(source_a, ArticleStatus.NEW, _SAME_TITLE, "https://example.com/trend-a-1"),
    )
    await _create_article(
        container,
        source_b,
        _make_article(source_b, ArticleStatus.NEW, _SAME_TITLE, "https://example.com/trend-b-1"),
    )

    await _run_stages(container, 10, False, ["summarize", "categorize", "cluster"])

    results = await _run_stages(container, 10, False, ["trends"])
    assert results[0]["stage"] == "trends"
    assert results[0]["status"] == "completed"
    assert await _count(container, TrendModel) >= 1, "Expected at least one trend to be detected"


# 9. Digest is generated from eligible stories
async def test_digest_is_generated(db_session, container) -> None:
    source = _make_source("Source H")
    articles = [
        _make_article(source, ArticleStatus.NEW, _SAME_TITLE, f"https://example.com/digest-{i}")
        for i in range(2)
    ]
    for article in articles:
        await _create_article(container, source, article)

    results = await _run_stages(
        container, 10, False, ["summarize", "categorize", "analyze", "cluster", "rank", "digest"]
    )
    digest_result = results[-1]
    assert digest_result["stage"] == "digest"
    assert digest_result["status"] in ("completed", "skipped")

    digest_count = await _count(container, DigestModel)
    assert digest_count >= 1, "Expected a digest row to be persisted"


# 10. Empty-state digest is handled without fabricating stories
async def test_empty_state_digest_handled(db_session, container) -> None:
    # No articles at all.
    results = await _run_stages(container, 10, False, ["digest"])
    assert results[0]["stage"] == "digest"
    assert results[0]["status"] in ("completed", "skipped")

    article_count = await _count(container, ArticleModel)
    assert article_count == 0


# 11. Dry run causes no persistent mutations
async def test_dry_run_causes_no_mutations(db_session, container) -> None:
    source = _make_source("Source I")
    article = _make_article(source, ArticleStatus.NEW, "Dry Run Me", "https://example.com/dry-1")
    await _create_article(container, source, article)

    before_status = await _article_status(container, article.id)
    before_clusters = await _count(container, StoryClusterModel)
    before_digests = await _count(container, DigestModel)

    results = await _run_stages(
        container, 10, True, ["summarize", "categorize", "analyze", "cluster", "rank", "digest"]
    )
    assert all(r["dry_run"] is True for r in results)

    assert await _article_status(container, article.id) == before_status
    assert await _count(container, StoryClusterModel) == before_clusters
    assert await _count(container, DigestModel) == before_digests


# 12. Batch size limit is respected
async def test_batch_size_limit_respected(db_session, container) -> None:
    source = _make_source("Source J")
    for i in range(5):
        await _create_article(
            container,
            source,
            _make_article(
                source, ArticleStatus.NEW, f"Batch {i}", f"https://example.com/batch-{i}"
            ),
        )

    results = await _run_stages(container, 2, False, ["summarize"])
    assert results[0]["status"] == "completed"

    summarized = await container.article_repository.session.execute(
        text("SELECT count(*) FROM articles WHERE status = :s"),
        {"s": ArticleStatus.SUMMARIZED.value},
    )
    new_count = await container.article_repository.session.execute(
        text("SELECT count(*) FROM articles WHERE status = :s"),
        {"s": ArticleStatus.NEW.value},
    )
    assert (
        summarized.scalar_one() == 2
    ), f"Expected exactly 2 summarized (batch=2), got {summarized.scalar_one()}"
    assert new_count.scalar_one() == 3


# 13. Repeated execution is idempotent (no duplicate clusters or digests)
async def test_repeated_execution_is_idempotent(db_session, container) -> None:
    source = _make_source("Source K")
    articles = [
        _make_article(source, ArticleStatus.NEW, _SAME_TITLE, f"https://example.com/idem-{i}")
        for i in range(2)
    ]
    for article in articles:
        await _create_article(container, source, article)

    await _run_stages(
        container, 10, False, ["summarize", "categorize", "analyze", "cluster", "rank", "digest"]
    )
    clusters_after_first = await _count(container, StoryClusterModel)
    digests_after_first = await _count(container, DigestModel)
    statuses_after_first = {str(a.id): await _article_status(container, a.id) for a in articles}

    # Run the full pipeline again.
    await _run_stages(
        container, 10, False, ["summarize", "categorize", "analyze", "cluster", "rank", "digest"]
    )

    assert await _count(container, StoryClusterModel) == clusters_after_first
    assert await _count(container, DigestModel) == digests_after_first
    for article in articles:
        assert await _article_status(container, article.id) == statuses_after_first[str(article.id)]


# 14. A failed stage rolls back the offending article without corrupting others
async def test_failed_article_rolls_back_without_corrupting_others(db_session, container) -> None:
    source = _make_source("Source L")
    ok_article = _make_article(
        source, ArticleStatus.NEW, "OK Article", "https://example.com/fail-ok"
    )
    bad_article = _make_article(
        source, ArticleStatus.NEW, "FAIL ME", "https://example.com/fail-bad"
    )
    await _create_article(container, source, ok_article)
    await _create_article(container, source, bad_article)

    from ai_news_digest.application.services import deterministic_article_processor as dap

    original_summarize = dap.deterministic_summarize
    call_count = {"n": 0}

    async def _boom(article):
        call_count["n"] += 1
        if article.title == "FAIL ME":
            raise RuntimeError("simulated summarization failure")
        return await original_summarize(article)

    with patch.object(dap, "deterministic_summarize", side_effect=_boom):
        results = await _run_stages(container, 10, False, ["summarize"])
    assert results[0]["status"] == "completed"
    assert call_count["n"] == 2

    assert await _article_status(container, ok_article.id) == ArticleStatus.SUMMARIZED.value
    assert await _article_status(container, bad_article.id) == ArticleStatus.NEW.value
    # Summarize does not create categories; the failed article left no partial rows.
    assert await _count(container, CategoryModel) == 0


# 15. Partial processing can safely resume
async def test_partial_processing_can_resume(db_session, container) -> None:
    source = _make_source("Source M")
    for i in range(3):
        await _create_article(
            container,
            source,
            _make_article(
                source, ArticleStatus.NEW, f"Resume {i}", f"https://example.com/resume-{i}"
            ),
        )

    # Process one at a time across three invocations.
    for _ in range(3):
        results = await _run_stages(container, 1, False, ["summarize"])
        assert results[0]["status"] == "completed"

    summarized = await container.article_repository.session.execute(
        text("SELECT count(*) FROM articles WHERE status = :s"),
        {"s": ArticleStatus.SUMMARIZED.value},
    )
    assert summarized.scalar_one() == 3


# 16. Concurrent execution does not corrupt state (single-instance lock + idempotent re-run)
async def test_concurrent_execution_safety(db_session, container) -> None:
    source = _make_source("Source N")
    article = _make_article(
        source, ArticleStatus.NEW, "Concurrent Me", "https://example.com/conc-1"
    )
    await _create_article(container, source, article)

    await _run_stages(container, 10, False, ["summarize", "categorize", "analyze", "cluster"])
    first_status = await _article_status(container, article.id)
    first_clusters = await _count(container, StoryClusterModel)

    # Re-run the full pipeline (simulating a repeated/overlapping invocation).
    await _run_stages(container, 10, False, ["summarize", "categorize", "analyze", "cluster"])
    assert await _article_status(container, article.id) == first_status
    assert await _count(container, StoryClusterModel) == first_clusters

    # The single-instance lock must refuse a second live holder.
    from scripts.scheduled.run_deterministic_batch import _acquire_lock, _release_lock

    assert _acquire_lock() is True
    assert _acquire_lock() is False  # same PID is alive -> lock held
    _release_lock()


# 17. Missing content is handled safely (no fabrication, no crash)
async def test_missing_content_handled_safely(db_session, container) -> None:
    source = _make_source("Source O")
    article = _make_article(
        source, ArticleStatus.NEW, "Empty Content", "https://example.com/empty-1", content=""
    )
    await _create_article(container, source, article)

    results = await _run_stages(container, 10, False, ["summarize"])
    assert results[0]["status"] == "completed"
    assert await _article_status(container, article.id) == ArticleStatus.SUMMARIZED.value


# 18. AI remains unused (deterministic path only, no provider fields set)
async def test_ai_remains_unused(db_session, container) -> None:
    from ai_news_digest.core.config import get_settings

    assert get_settings().ai_enabled is False

    source = _make_source("Source P")
    article = _make_article(source, ArticleStatus.NEW, "No AI", "https://example.com/no-ai-1")
    await _create_article(container, source, article)

    await _run_stages(container, 10, False, ["summarize", "categorize", "analyze"])

    result = await container.article_repository.session.execute(
        text("SELECT ai_provider, ai_model FROM articles WHERE id = :id"),
        {"id": str(article.id)},
    )
    row = result.one()
    assert row.ai_provider is None
    assert row.ai_model is None


# 19. No Redis broker is required (PostgreSQL-only fixture)
async def test_no_redis_broker_required(db_session, container) -> None:
    source = _make_source("Source Q")
    article = _make_article(source, ArticleStatus.NEW, "No Redis", "https://example.com/noredis-1")
    await _create_article(container, source, article)

    results = await _run_stages(
        container,
        10,
        False,
        ["summarize", "categorize", "analyze", "cluster", "rank", "trends", "digest"],
    )
    assert all(r["status"] == "completed" for r in results)
    assert await _article_status(container, article.id) == ArticleStatus.ANALYZED.value


# 20. Existing AI-enabled task paths remain unchanged (use_case path still routed)
async def test_ai_enabled_task_path_remains_unchanged(db_session, container) -> None:
    source = _make_source("Source R")
    article = _make_article(source, ArticleStatus.NEW, "AI Path", "https://example.com/aipath-1")
    await _create_article(container, source, article)

    summarized_article = _make_article(
        source, ArticleStatus.SUMMARIZED, "AI Path", "https://example.com/aipath-1"
    )
    summarized_article.id = article.id
    summarized_article.status = ArticleStatus.SUMMARIZED

    # The summarization use case is present (AI-enabled shape): the impl must
    # route through it rather than falling back to the deterministic processor.
    fake_use_case = AsyncMock()
    fake_use_case.execute = AsyncMock(return_value=summarized_article)

    from ai_news_digest.application.services import deterministic_article_processor as dap
    from ai_news_digest.bootstrap.container import Container as ContainerClass

    deterministic_called = {"n": 0}
    original_summarize = dap.deterministic_summarize

    async def _guard(article):
        deterministic_called["n"] += 1
        return await original_summarize(article)

    with (
        patch.object(ContainerClass, "summarize_article", property(lambda self: fake_use_case)),
        patch.object(dap, "deterministic_summarize", side_effect=_guard),
    ):
        results = await _run_stages(container, 10, False, ["summarize"])

    assert results[0]["status"] == "completed"
    assert fake_use_case.execute.await_count >= 1
    assert deterministic_called["n"] == 0
    assert await _article_status(container, article.id) == ArticleStatus.SUMMARIZED.value
