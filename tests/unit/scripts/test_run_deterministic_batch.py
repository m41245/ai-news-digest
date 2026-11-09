"""
Unit tests for ``scripts/scheduled/run_deterministic_batch.py``.

These tests exercise the batch runner against a mocked container so the
stage dispatch, dry-run reporting, ordering, and failure handling are
verified without a database, broker, or external services.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import scripts.scheduled.run_deterministic_batch as batch_module
from scripts.scheduled.run_deterministic_batch import _parse_args, _run_pipeline, _run_stage, main

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
    container.article_repository.list_by_status.return_value = [MagicMock()] * 7

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
    assert result["processed"] == 10  # categorized + summarized


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
