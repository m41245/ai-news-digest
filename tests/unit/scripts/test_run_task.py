"""
Unit tests for ``scripts/scheduled/run_task.py``.

Covers task dispatch, exit codes, async execution, and environment validation
for the direct runner.
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import scripts.scheduled.run_task as run_task_module
from scripts.scheduled.run_task import _import_impl, run_task


_ALL_BEAT_TASKS = [
    "ingest",
    "summarize",
    "categorize",
    "analyze",
    "cluster",
    "timeline",
    "ranking",
    "conflict",
    "story-activity",
    "trend",
    "evaluation",
    "quality-gates",
    "digest",
    "deliver",
    "notifications-schedule",
    "notifications-scheduled",
    "notifications-immediate",
    "notifications-retry",
    "notifications-recover",
    "notifications-cleanup-deliveries",
    "notifications-cleanup",
]


@pytest.mark.parametrize("task_name", _ALL_BEAT_TASKS)
def test_import_impl_returns_callable_for_all_beat_tasks(task_name: str) -> None:
    impl = _import_impl(task_name)
    assert callable(impl), f"Impl for {task_name} is not callable"


def test_import_impl_raises_for_unknown_task() -> None:
    with pytest.raises(ValueError, match="Unknown task: does-not-exist"):
        _import_impl("does-not-exist")


@pytest.mark.asyncio
async def test_run_task_unknown_task_returns_one() -> None:
    result = await run_task("does-not-exist")
    assert result == 1


@pytest.mark.asyncio
async def test_run_task_success_returns_zero() -> None:
    fake_impl = AsyncMock(return_value={"status": "completed"})
    with patch.object(run_task_module, "_import_impl", return_value=fake_impl):
        result = await run_task("ingest")
    assert result == 0
    fake_impl.assert_called_once()


@pytest.mark.asyncio
async def test_run_task_failure_returns_one() -> None:
    fake_impl = AsyncMock(side_effect=RuntimeError("boom"))
    with patch.object(run_task_module, "_import_impl", return_value=fake_impl):
        result = await run_task("ingest")
    assert result == 1


@pytest.mark.asyncio
async def test_run_task_sync_impl_success_returns_zero() -> None:
    fake_impl = MagicMock(return_value={"status": "completed"})
    with patch.object(run_task_module, "_import_impl", return_value=fake_impl):
        result = await run_task("ingest")
    assert result == 0
    fake_impl.assert_called_once()


@pytest.mark.asyncio
async def test_run_task_sync_impl_failure_returns_one() -> None:
    fake_impl = MagicMock(side_effect=RuntimeError("boom"))
    with patch.object(run_task_module, "_import_impl", return_value=fake_impl):
        result = await run_task("ingest")
    assert result == 1


@pytest.mark.asyncio
async def test_run_task_logs_success() -> None:
    fake_impl = AsyncMock(return_value={"status": "completed"})
    with (
        patch.object(run_task_module, "_import_impl", return_value=fake_impl),
        patch.object(run_task_module.logger, "info") as mock_info,
    ):
        result = await run_task("ingest")
    assert result == 0
    mock_info.assert_called_once()
    assert mock_info.call_args.kwargs["task"] == "ingest"


@pytest.mark.asyncio
async def test_run_task_logs_failure() -> None:
    fake_impl = AsyncMock(side_effect=RuntimeError("boom"))
    with (
        patch.object(run_task_module, "_import_impl", return_value=fake_impl),
        patch.object(run_task_module.logger, "error") as mock_error,
    ):
        result = await run_task("ingest")
    assert result == 1
    mock_error.assert_called_once()
    assert mock_error.call_args.kwargs["task"] == "ingest"


def test_main_parses_task_argument() -> None:
    with patch.object(run_task_module, "run_task", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = 0
        with patch.object(sys, "argv", ["run_task.py", "ingest"]):
            run_task_module.main()
    mock_run.assert_called_once_with("ingest")
