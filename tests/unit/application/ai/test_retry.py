"""
Unit tests for the RetryPolicy.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from ai_news_digest.application.ai.errors import (
    AIAuthenticationError,
    AITransientError,
)
from ai_news_digest.application.ai.retry import RetryPolicy


def test_retry_policy_invalid_max_attempts() -> None:
    """max_attempts must be >= 1."""
    with pytest.raises(ValueError, match="max_attempts must be >= 1"):
        RetryPolicy(max_attempts=0)


@pytest.mark.asyncio
async def test_retry_policy_succeeds_first_try() -> None:
    """A successful call is returned without retry."""
    policy = RetryPolicy(max_attempts=3, base_delay=0.01, max_delay=0.02)
    mock_func = AsyncMock(return_value="ok")

    result = await policy.execute(mock_func, "arg1", kw1="v1")

    assert result == "ok"
    mock_func.assert_awaited_once_with("arg1", kw1="v1")


@pytest.mark.asyncio
async def test_retry_policy_retries_transient_errors() -> None:
    """Transient errors are retried up to max_attempts."""
    policy = RetryPolicy(max_attempts=3, base_delay=0.01, max_delay=0.02)
    mock_func = AsyncMock(side_effect=[AITransientError("t1"), AITransientError("t2"), "ok"])

    result = await policy.execute(mock_func)

    assert result == "ok"
    assert mock_func.await_count == 3


@pytest.mark.asyncio
async def test_retry_policy_raises_after_exhausting_retries() -> None:
    """When all retries fail, the last transient error is raised."""
    policy = RetryPolicy(max_attempts=3, base_delay=0.01, max_delay=0.02)
    mock_func = AsyncMock(side_effect=AITransientError("persistent"))

    with pytest.raises(AITransientError, match="persistent"):
        await policy.execute(mock_func)

    assert mock_func.await_count == 3


@pytest.mark.asyncio
async def test_retry_policy_does_not_retry_permanent_errors() -> None:
    """Permanent errors are raised immediately without retry."""
    policy = RetryPolicy(max_attempts=3, base_delay=0.01, max_delay=0.02)
    mock_func = AsyncMock(side_effect=AIAuthenticationError("bad key"))

    with pytest.raises(AIAuthenticationError, match="bad key"):
        await policy.execute(mock_func)

    assert mock_func.await_count == 1


@pytest.mark.asyncio
async def test_retry_policy_does_not_retry_generic_errors() -> None:
    """Non-AI errors are raised immediately without retry."""
    policy = RetryPolicy(max_attempts=3, base_delay=0.01, max_delay=0.02)
    mock_func = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        await policy.execute(mock_func)

    assert mock_func.await_count == 1
