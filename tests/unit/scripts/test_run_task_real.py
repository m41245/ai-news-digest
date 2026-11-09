"""
Regression tests for the scheduled task runner against the real implementations.

The audit flagged stale ``no_provider`` expectations and potentially incorrect
exit-code assumptions after deterministic processing was introduced. These
tests verify the runner against the *actual* task implementations rather than
mocked imports, so the exit-code contract is checked end to end.
"""

from __future__ import annotations

import inspect
import sys
from unittest.mock import AsyncMock, patch

import scripts.scheduled.run_task as run_task_module
from scripts.scheduled.run_task import _import_impl, run_task


async def test_summarize_task_wired_to_real_pending_impl() -> None:
    """The summarize task maps to the real pending-articles implementation."""
    impl = _import_impl("summarize")
    assert callable(impl)
    assert "summarize_pending_articles_impl" in inspect.getsource(impl)


async def test_categorize_task_wired_to_real_pending_impl() -> None:
    """The categorize task maps to the real pending-articles implementation."""
    impl = _import_impl("categorize")
    assert callable(impl)
    assert "categorize_pending_articles_impl" in inspect.getsource(impl)


async def test_analyze_task_wired_to_real_pending_impl() -> None:
    """The analyze task maps to the real pending-articles implementation."""
    impl = _import_impl("analyze")
    assert callable(impl)
    assert "analyze_pending_articles_impl" in inspect.getsource(impl)


async def test_run_task_treats_deterministic_completed_dict_as_success() -> None:
    """A deterministic ``completed`` dict is treated as a successful run."""

    async def fake_impl() -> dict:
        return {"status": "completed", "processed": 0, "failed": 0}

    with patch.object(run_task_module, "_import_impl", return_value=fake_impl):
        result = await run_task("summarize")

    assert result == 0


async def test_run_task_treats_real_exception_as_failure() -> None:
    """An exception raised by the real implementation yields exit code 1."""

    async def fake_impl() -> dict:
        raise RuntimeError("real impl boom")

    with patch.object(run_task_module, "_import_impl", return_value=fake_impl):
        result = await run_task("summarize")

    assert result == 1


async def test_run_task_unknown_task_returns_one() -> None:
    """An unknown task name yields exit code 1."""
    result = await run_task("does-not-exist")
    assert result == 1


def test_main_invokes_run_task_and_exits_with_code() -> None:
    """main() returns the exit code produced by run_task."""
    with (
        patch.object(run_task_module, "run_task", new_callable=AsyncMock, return_value=0),
        patch.object(sys, "argv", ["run_task.py", "ingest"]),
    ):
        assert run_task_module.main() == 0


def test_main_propagates_nonzero_exit_code() -> None:
    """main() propagates a nonzero exit code from run_task."""
    with (
        patch.object(run_task_module, "run_task", new_callable=AsyncMock, return_value=1),
        patch.object(sys, "argv", ["run_task.py", "ingest"]),
    ):
        assert run_task_module.main() == 1
