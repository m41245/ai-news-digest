"""
Unit tests for ``scripts/scheduled/run_deterministic_batch.py``.

These tests exercise the batch runner against a mocked container so the
stage dispatch, dry-run reporting, ordering, and failure handling are
verified without a database, broker, or external services.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import scripts.scheduled.run_deterministic_batch as batch_module
from scripts.scheduled.run_deterministic_batch import (
    _parse_args,
    _run_pipeline,
    _run_stage,
    main,
)

from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article

pytestmark = pytest.mark.unit


def _make_container() -> MagicMock:
    container = MagicMock()
    container.article_repository = MagicMock()
    container.article_repository.list_by_status = AsyncMock(return_value=[])
    return container


async def _async_gen(container):
    yield container


def _patch_container(container: MagicMock):
    return patch.object(batch_module, "get_container", return_value=_async_gen(container))


def _make_test_article(
    *,
    status: ArticleStatus = ArticleStatus.NEW,
    content: str | None = "Valid article content here about AI.",
    summary: str | None = "",
    title: str = "Test Article",
    cluster_id: object | None = None,
) -> Article:
    article = Article.create(
        title=title,
        url=f"https://example.com/{uuid4()}",
        summary=summary,
        content=content,
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )
    article.status = status
    article.cluster_id = cluster_id
    return article


def test_parse_args_defaults() -> None:
    with patch.object(
        batch_module.sys, "argv", ["run_deterministic_batch.py", "--batch-size", "50"]
    ):
        args = _parse_args()
    assert args.batch_size == 50
    assert args.dry_run is False
    assert args.stages == "summarize, categorize, analyze, cluster, rank, trends, digest"
    assert args.skip_stages == ""


def test_parse_args_dry_run() -> None:
    with patch.object(
        batch_module.sys,
        "argv",
        ["run_deterministic_batch.py", "--dry-run", "--stages", "summarize,categorize"],
    ):
        args = _parse_args()
    assert args.dry_run is True
    assert args.stages == "summarize,categorize"


def test_parse_args_skip_stages() -> None:
    with patch.object(
        batch_module.sys,
        "argv",
        ["run_deterministic_batch.py", "--skip-stages", "trends,digest"],
    ):
        args = _parse_args()
    assert args.skip_stages == "trends,digest"


def test_main_invalid_stage_returns_one() -> None:
    with (
        patch.object(
            batch_module.sys,
            "argv",
            ["run_deterministic_batch.py", "--stages", "bogus"],
        ),
        patch.object(batch_module.logger, "error") as mock_error,
    ):
        result = main()
    assert result == 1
    mock_error.assert_called()


def test_main_no_stages_selected_returns_one() -> None:
    with (
        patch.object(
            batch_module.sys,
            "argv",
            ["run_deterministic_batch.py", "--stages", "summarize", "--skip-stages", "summarize"],
        ),
        patch.object(batch_module.logger, "error") as mock_error,
    ):
        result = main()
    assert result == 1
    mock_error.assert_called()


async def test_run_stage_summarize_dry_run_reports_count() -> None:
    container = _make_container()
    articles = [
        _make_test_article(
            status=ArticleStatus.NEW, content=f"Valid article number {i} content here."
        )
        for i in range(7)
    ]
    container.article_repository.list_by_status.return_value = articles

    with _patch_container(container):
        result = await _run_stage("summarize", 100, dry_run=True, container=container)

    assert result["stage"] == "summarize"
    assert result["dry_run"] is True
    assert result["status"] == "would_process"
    assert result["processed"] == 7


async def test_run_stage_categorize_dry_run_reports_count() -> None:
    container = _make_container()
    container.article_repository.list_by_status.return_value = [MagicMock()] * 3

    with _patch_container(container):
        result = await _run_stage("categorize", 100, dry_run=True, container=container)

    assert result["stage"] == "categorize"
    assert result["status"] == "would_process"
    assert result["processed"] == 3


async def test_run_stage_analyze_dry_run_reports_count() -> None:
    container = _make_container()
    container.article_repository.list_by_status.return_value = [MagicMock()] * 5

    with _patch_container(container):
        result = await _run_stage("analyze", 100, dry_run=True, container=container)

    assert result["stage"] == "analyze"
    assert result["status"] == "would_process"
    assert result["processed"] == 5  # CATEGORIZED articles only (batch path)


async def test_run_pipeline_executes_stages_in_order() -> None:
    container = _make_container()
    container.article_repository.list_by_status.return_value = []

    stage_order: list[str] = []

    async def fake_summarize(execute_directly=False, limit=100):
        stage_order.append("summarize")
        return {"queued": 0, "failed": 0}

    async def fake_categorize(execute_directly=False, limit=100):
        stage_order.append("categorize")
        return {"queued": 0, "failed": 0}

    async def fake_analyze(execute_directly=False, limit=100):
        stage_order.append("analyze")
        return {"queued": 0, "failed": 0}

    async def fake_cluster(execute_directly=False, limit=100):
        stage_order.append("cluster")
        return {"queued": 0}

    async def fake_rank():
        stage_order.append("rank")
        return {"status": "completed", "ranked_clusters": "0"}

    async def fake_trends():
        stage_order.append("trends")
        return {"status": "completed", "detected": 0}

    async def fake_digest():
        stage_order.append("digest")
        return {"status": "completed", "included_articles": 0}

    with (
        _patch_container(container),
        patch.object(batch_module, "_summarize_pending_articles_impl", fake_summarize),
        patch.object(batch_module, "_categorize_pending_articles_impl", fake_categorize),
        patch.object(batch_module, "_analyze_pending_articles_impl", fake_analyze),
        patch.object(batch_module, "_cluster_pending_articles_impl", fake_cluster),
        patch.object(batch_module, "_rank_stories_impl", fake_rank),
        patch.object(batch_module, "_detect_trends_impl", fake_trends),
        patch.object(batch_module, "_generate_daily_digest_impl", fake_digest),
    ):
        results = await _run_pipeline(
            100,
            dry_run=False,
            stages=["summarize", "categorize", "analyze", "cluster", "rank", "trends", "digest"],
        )

    assert stage_order == [
        "summarize",
        "categorize",
        "analyze",
        "cluster",
        "rank",
        "trends",
        "digest",
    ]
    assert len(results) == 7
    assert all(r["status"] == "completed" for r in results)


async def test_run_pipeline_stops_on_failed_stage() -> None:
    container = _make_container()
    container.article_repository.list_by_status.return_value = []

    async def fake_summarize(execute_directly=False, limit=100):
        return {"queued": 0, "failed": 0}

    async def fake_failing_stage(execute_directly=False, limit=100):
        raise RuntimeError("stage boom")

    with (
        _patch_container(container),
        patch.object(batch_module, "_summarize_pending_articles_impl", fake_summarize),
        patch.object(batch_module, "_categorize_pending_articles_impl", fake_failing_stage),
        patch.object(batch_module, "_analyze_pending_articles_impl", fake_summarize),
        patch.object(batch_module, "_cluster_pending_articles_impl", fake_summarize),
        patch.object(batch_module, "_rank_stories_impl", fake_summarize),
        patch.object(batch_module, "_detect_trends_impl", fake_summarize),
        patch.object(batch_module, "_generate_daily_digest_impl", fake_summarize),
    ):
        results = await _run_pipeline(
            100,
            dry_run=False,
            stages=["summarize", "categorize", "analyze", "cluster", "rank", "trends", "digest"],
        )

    # Should stop after categorize fails; later stages should not run.
    statuses = [r["status"] for r in results]
    assert statuses == ["completed", "failed"]


async def test_run_pipeline_returns_success_on_all_stages() -> None:
    """The full pipeline returns success when all stages complete."""
    container = _make_container()
    container.article_repository.list_by_status.return_value = []

    async def fake_impl(*_args, **_kwargs):
        return {"queued": 0, "failed": 0, "status": "completed"}

    async def fake_rank():
        return {
            "status": "completed",
            "ranked_clusters": "0",
            "top_story_cluster_id": "",
            "top_story_score": "",
            "min_score": "0.0",
            "max_score": "0.0",
        }

    async def fake_trends():
        return {"status": "completed", "detected": 0}

    async def fake_digest():
        return {"status": "completed", "included_articles": 0}

    with (
        _patch_container(container),
        patch.object(batch_module, "_summarize_pending_articles_impl", fake_impl),
        patch.object(batch_module, "_categorize_pending_articles_impl", fake_impl),
        patch.object(batch_module, "_analyze_pending_articles_impl", fake_impl),
        patch.object(batch_module, "_cluster_pending_articles_impl", fake_impl),
        patch.object(batch_module, "_rank_stories_impl", fake_rank),
        patch.object(batch_module, "_detect_trends_impl", fake_trends),
        patch.object(batch_module, "_generate_daily_digest_impl", fake_digest),
    ):
        results = await _run_pipeline(
            100,
            dry_run=False,
            stages=["summarize", "categorize", "analyze", "cluster", "rank", "trends", "digest"],
        )

    assert len(results) == 7
    assert all(r["status"] == "completed" for r in results)


def test_main_exits_zero_with_successful_pipeline() -> None:
    """main() returns 0 when the pipeline completes successfully."""
    container = _make_container()
    container.article_repository.list_by_status.return_value = []

    async def fake_pipeline(*_args, **_kwargs):
        return [
            {"stage": "summarize", "status": "completed", "processed": 0, "failed": 0},
        ]

    with (
        _patch_container(container),
        patch.object(
            batch_module.sys, "argv", ["run_deterministic_batch.py", "--stages", "summarize"]
        ),
        patch.object(batch_module, "_run_pipeline", fake_pipeline),
    ):
        result = main()

    assert result == 0


def test_main_exits_nonzero_on_pipeline_failure() -> None:
    """main() returns 1 when a stage fails."""
    container = _make_container()
    container.article_repository.list_by_status.return_value = []

    async def fake_pipeline(*_args, **_kwargs):
        return [
            {"stage": "summarize", "status": "completed", "processed": 0, "failed": 0},
            {"stage": "categorize", "status": "failed", "processed": 0, "failed": 1},
        ]

    with (
        _patch_container(container),
        patch.object(
            batch_module.sys,
            "argv",
            ["run_deterministic_batch.py", "--stages", "summarize,categorize"],
        ),
        patch.object(batch_module, "_run_pipeline", fake_pipeline),
    ):
        result = main()

    assert result == 1


# ----------------------------------------------------------------------
# Dry-run accuracy tests
# ----------------------------------------------------------------------


async def test_dry_run_summarize_reports_eligible_count_only() -> None:
    """Dry-run summarize counts only NEW articles that pass content eligibility."""
    eligible = _make_test_article(
        status=ArticleStatus.NEW, content="Real article content about AI."
    )
    ineligible_none = _make_test_article(status=ArticleStatus.NEW, content=None, summary=None)
    ineligible_empty = _make_test_article(status=ArticleStatus.NEW, content="", summary=None)
    ineligible_html = _make_test_article(
        status=ArticleStatus.NEW, content="<script>alert(1)</script>", summary=None
    )

    container = _make_container()
    container.article_repository.list_by_status.return_value = [
        eligible,
        ineligible_none,
        ineligible_empty,
        ineligible_html,
    ]

    with _patch_container(container):
        result = await _run_stage("summarize", 100, dry_run=True, container=container)

    assert result["stage"] == "summarize"
    assert result["dry_run"] is True
    assert result["eligible"] == 1
    assert result["would_process"] == 1
    assert result["processed"] == 1
    assert result["status"] == "would_process"


async def test_dry_run_summarize_applies_batch_limit() -> None:
    """Dry-run summarize does not count beyond the batch-size selection."""
    articles = [
        _make_test_article(
            status=ArticleStatus.NEW,
            content=f"Valid article number {i} with sufficient content here.",
        )
        for i in range(5)
    ]

    container = _make_container()
    container.article_repository.list_by_status.side_effect = lambda status, limit=100: articles[
        :limit
    ]

    with _patch_container(container):
        result = await _run_stage("summarize", 2, dry_run=True, container=container)

    assert result["eligible"] == 2
    assert result["would_process"] == 2
    assert result["processed"] == 2
    assert result["status"] == "would_process"


async def test_dry_run_summarize_existing_summary_counts_as_eligible() -> None:
    """NEW articles with a valid existing summary are eligible even with None content."""
    with_summary = _make_test_article(
        status=ArticleStatus.NEW,
        content=None,
        summary=None,
        title="T",
    )
    # Override to have a valid summary but None content
    with_summary.content = None
    with_summary.summary = "A valid pre-existing summary."

    container = _make_container()
    container.article_repository.list_by_status.return_value = [with_summary]

    with _patch_container(container):
        result = await _run_stage("summarize", 100, dry_run=True, container=container)

    assert result["eligible"] == 1
    assert result["would_process"] == 1


async def test_dry_run_categorize_reports_summarized_count() -> None:
    """Dry-run categorize counts SUMMARIZED articles (all are eligible)."""
    articles = [
        _make_test_article(status=ArticleStatus.SUMMARIZED, content="x" * 50) for _ in range(4)
    ]
    container = _make_container()
    container.article_repository.list_by_status.return_value = articles

    with _patch_container(container):
        result = await _run_stage("categorize", 100, dry_run=True, container=container)

    assert result["eligible"] == 4
    assert result["would_process"] == 4
    assert result["status"] == "would_process"


async def test_dry_run_analyze_reports_categorized_count() -> None:
    """Dry-run analyze counts CATEGORIZED articles (matching the batch path)."""
    articles = [
        _make_test_article(status=ArticleStatus.CATEGORIZED, content="x" * 50) for _ in range(3)
    ]
    container = _make_container()
    container.article_repository.list_by_status.return_value = articles

    with _patch_container(container):
        result = await _run_stage("analyze", 100, dry_run=True, container=container)

    assert result["eligible"] == 3
    assert result["would_process"] == 3
    assert result["status"] == "would_process"


async def test_dry_run_cluster_excludes_already_clustered() -> None:
    """Dry-run cluster excludes articles that already have a cluster_id."""
    unclustered = _make_test_article(status=ArticleStatus.CATEGORIZED, cluster_id=None)
    clustered = _make_test_article(status=ArticleStatus.SUMMARIZED, cluster_id=uuid4())
    unclustered2 = _make_test_article(status=ArticleStatus.ANALYZED, cluster_id=None)

    container = _make_container()
    # Return different lists per status call
    container.article_repository.list_by_status.side_effect = [
        [unclustered],  # CATEGORIZED
        [clustered],  # SUMMARIZED
        [unclustered2],  # ANALYZED
        [],  # READY
    ]

    with _patch_container(container):
        result = await _run_stage("cluster", 100, dry_run=True, container=container)

    assert result["eligible"] == 2
    assert result["would_process"] == 2
    assert result["status"] == "would_process"


async def test_dry_run_cluster_applies_batch_limit() -> None:
    """Dry-run cluster caps eligible count at batch_size, matching live selection."""
    articles = [
        _make_test_article(status=ArticleStatus.CATEGORIZED, cluster_id=None) for _ in range(10)
    ]
    container = _make_container()
    container.article_repository.list_by_status.side_effect = [
        articles,  # CATEGORIZED - 10 articles, mock ignores limit
        [],  # SUMMARIZED
        [],  # ANALYZED
        [],  # READY
    ]

    with _patch_container(container):
        result = await _run_stage("cluster", 3, dry_run=True, container=container)

    assert result["eligible"] == 3
    assert result["would_process"] == 3
    assert result["processed"] == 3
    assert result["status"] == "would_process"


async def test_dry_run_rank_trends_digest_are_not_evaluated() -> None:
    """Rank, trends, digest cannot be counted read-only; report not_evaluated."""
    container = _make_container()

    for stage in ("rank", "trends", "digest"):
        with _patch_container(container):
            result = await _run_stage(stage, 100, dry_run=True, container=container)

        assert result["status"] == "not_evaluated"
        assert result["not_evaluated"] is True
        assert result["eligible"] == 0
        assert result["would_process"] == 0
        assert "cannot" in result["note"]


async def test_dry_run_no_negative_one_sentinel() -> None:
    """No stage should report -1 as a count."""
    container = _make_container()

    for stage in (
        "summarize",
        "categorize",
        "analyze",
        "cluster",
        "rank",
        "trends",
        "digest",
    ):
        with _patch_container(container):
            result = await _run_stage(stage, 100, dry_run=True, container=container)

        for key in ("eligible", "would_process", "processed", "skipped_ineligible", "failed"):
            assert result[key] >= 0, f"Stage {stage} has negative {key}: {result[key]}"
        assert result["processed"] != -1


# ----------------------------------------------------------------------
# Dry-run zero-mutation tests
# ----------------------------------------------------------------------


async def test_dry_run_summarize_does_not_mutate_articles() -> None:
    """Dry-run must not mutate ORM objects or change article status."""
    article = _make_test_article(status=ArticleStatus.NEW, content="Valid content.")
    original_status = article.status
    original_summary = article.summary

    container = _make_container()
    container.article_repository.list_by_status.return_value = [article]

    with _patch_container(container):
        result = await _run_stage("summarize", 100, dry_run=True, container=container)

    assert article.status == original_status
    assert article.summary == original_summary
    assert result["status"] == "would_process"


async def test_dry_run_cluster_does_not_mutate_cluster_id() -> None:
    """Dry-run cluster must not set or change cluster_id on articles."""
    article = _make_test_article(status=ArticleStatus.CATEGORIZED, cluster_id=None)
    original_cluster_id = article.cluster_id

    container = _make_container()
    container.article_repository.list_by_status.side_effect = [
        [article],
        [],
        [],
        [],
    ]

    with _patch_container(container):
        result = await _run_stage("cluster", 100, dry_run=True, container=container)

    assert article.cluster_id == original_cluster_id
    assert result["status"] == "would_process"


async def test_dry_run_does_not_invoke_stage_implementations() -> None:
    """Dry-run must not call the live stage implementation functions."""
    container = _make_container()
    container.article_repository.list_by_status.return_value = []

    called = []

    async def fake_summarize(*args, **kwargs):
        called.append("summarize")
        return {"queued": 0, "failed": 0}

    with (
        _patch_container(container),
        patch.object(batch_module, "_summarize_pending_articles_impl", fake_summarize),
        patch.object(batch_module, "_categorize_pending_articles_impl", fake_summarize),
        patch.object(batch_module, "_analyze_pending_articles_impl", fake_summarize),
        patch.object(batch_module, "_cluster_pending_articles_impl", fake_summarize),
    ):
        for stage in ("summarize", "categorize", "analyze", "cluster"):
            await _run_stage(stage, 100, dry_run=True, container=container)

    assert called == [], f"Stage implementations were invoked during dry-run: {called}"


# ----------------------------------------------------------------------
# Dry-run duplicate relationship tests
# ----------------------------------------------------------------------


async def test_dry_run_cluster_no_duplicate_counting_across_statuses() -> None:
    """Each article appears under exactly one status and is counted once."""
    categorized = _make_test_article(status=ArticleStatus.CATEGORIZED, cluster_id=None)
    summarized = _make_test_article(status=ArticleStatus.SUMMARIZED, cluster_id=None)
    analyzed = _make_test_article(status=ArticleStatus.ANALYZED, cluster_id=None)
    already_clustered = _make_test_article(status=ArticleStatus.READY, cluster_id=uuid4())

    container = _make_container()
    container.article_repository.list_by_status.side_effect = [
        [categorized],  # CATEGORIZED
        [summarized],  # SUMMARIZED
        [analyzed],  # ANALYZED
        [already_clustered],  # READY - excluded because cluster_id is set
    ]

    with _patch_container(container):
        result = await _run_stage("cluster", 100, dry_run=True, container=container)

    assert result["eligible"] == 3
    assert result["would_process"] == 3


# ----------------------------------------------------------------------
# Batch runner lock behavior tests
# ----------------------------------------------------------------------


def test_acquire_lock_creates_and_releases_lock_file(tmp_path) -> None:
    """_acquire_lock writes the lock file and _release_lock removes it."""
    original_lock_path = batch_module._lock_path

    try:
        batch_module._lock_path = lambda: tmp_path / "test.lock"

        assert batch_module._acquire_lock() is True
        lock_file = tmp_path / "test.lock"
        assert lock_file.exists()
        assert lock_file.read_text().strip() == str(os.getpid())

        batch_module._release_lock()
        assert not lock_file.exists()
    finally:
        batch_module._lock_path = original_lock_path


def test_acquire_lock_rejects_live_holder(tmp_path) -> None:
    """_acquire_lock returns False when a live PID holds the lock."""
    original_lock_path = batch_module._lock_path

    try:
        batch_module._lock_path = lambda: tmp_path / "test.lock"

        # First acquire succeeds
        assert batch_module._acquire_lock() is True

        # Second acquire in the same process: the holder PID is this process,
        # which is alive, so the lock is "held" and the second acquire returns False.
        assert batch_module._acquire_lock() is False

        batch_module._release_lock()
    finally:
        batch_module._lock_path = original_lock_path


def test_acquire_lock_reclaims_stale_lock(tmp_path) -> None:
    """_acquire_lock reclaims a lock file left by a dead process."""
    original_lock_path = batch_module._lock_path

    try:
        batch_module._lock_path = lambda: tmp_path / "test.lock"

        # Write a lock file with a PID that cannot be alive
        lock_file = tmp_path / "test.lock"
        lock_file.write_text("999999", encoding="utf-8")

        # Should reclaim the stale lock
        assert batch_module._acquire_lock() is True
        assert lock_file.read_text().strip() == str(os.getpid())

        batch_module._release_lock()
        assert not lock_file.exists()
    finally:
        batch_module._lock_path = original_lock_path
