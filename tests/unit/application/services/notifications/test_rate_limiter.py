"""
Unit tests for ``NotificationRateLimiter``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.services.notifications.rate_limiter import (
    NotificationRateLimiter,
)
from ai_news_digest.core.config import get_settings


def _make_rate_limiter(delivery_repo: MagicMock) -> NotificationRateLimiter:
    return NotificationRateLimiter(delivery_repo=delivery_repo)


@pytest.fixture
def mock_delivery_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def rate_limiter(mock_delivery_repo: MagicMock) -> NotificationRateLimiter:
    return _make_rate_limiter(mock_delivery_repo)


@pytest.mark.asyncio
async def test_daily_cap_enforcement_per_user(
    rate_limiter: NotificationRateLimiter,
    mock_delivery_repo: MagicMock,
) -> None:
    user_id = uuid4()
    mock_delivery_repo.count_pending_since = AsyncMock(return_value=100)
    allowed, reason = await rate_limiter.check_and_record(user_id, "email")
    assert allowed is False
    assert reason == "user_daily_email_cap_reached"


@pytest.mark.asyncio
async def test_email_cap_enforcement(
    rate_limiter: NotificationRateLimiter,
    mock_delivery_repo: MagicMock,
) -> None:
    user_id = uuid4()
    mock_delivery_repo.count_pending_since = AsyncMock(return_value=100)
    allowed, reason = await rate_limiter.check_and_record(user_id, "email")
    assert allowed is False
    assert reason == "user_daily_email_cap_reached"


@pytest.mark.asyncio
async def test_digest_cap_enforcement(
    rate_limiter: NotificationRateLimiter,
    mock_delivery_repo: MagicMock,
) -> None:
    user_id = uuid4()
    mock_delivery_repo.count_pending_since = AsyncMock(return_value=100)
    allowed, reason = await rate_limiter.check_and_record(user_id, "digest")
    assert allowed is False
    assert reason == "global_rate_limit_exceeded"


@pytest.mark.asyncio
async def test_global_rate_limit_enforcement(
    rate_limiter: NotificationRateLimiter,
    mock_delivery_repo: MagicMock,
) -> None:
    user_id = uuid4()
    mock_delivery_repo.count_pending_since = AsyncMock(return_value=200)
    allowed, reason = await rate_limiter.check_and_record(user_id, "push")
    assert allowed is False
    assert reason == "global_rate_limit_exceeded"


@pytest.mark.asyncio
async def test_within_caps_allows_delivery(
    rate_limiter: NotificationRateLimiter,
    mock_delivery_repo: MagicMock,
) -> None:
    user_id = uuid4()
    mock_delivery_repo.count_pending_since = AsyncMock(return_value=5)
    allowed, reason = await rate_limiter.check_and_record(user_id, "email")
    assert allowed is True
    assert reason is None


@pytest.mark.asyncio
async def test_concurrent_access_does_not_bypass_caps(
    rate_limiter: NotificationRateLimiter,
    mock_delivery_repo: MagicMock,
) -> None:
    import asyncio
    user_id = uuid4()
    call_count = 0

    async def count_side_effect(*args: Any, **kwargs: Any) -> int:
        nonlocal call_count
        call_count += 1
        return 100

    mock_delivery_repo.count_pending_since = AsyncMock(side_effect=count_side_effect)
    tasks = [
        rate_limiter.check_and_record(user_id, "email"),
        rate_limiter.check_and_record(user_id, "email"),
    ]
    results = await asyncio.gather(*tasks)

    assert call_count == 2
    assert all(r[0] is False for r in results)
    assert all(r[1] == "user_daily_email_cap_reached" for r in results)


@pytest.mark.asyncio
async def test_suppressed_notifications_have_recorded_reason(
    rate_limiter: NotificationRateLimiter,
    mock_delivery_repo: MagicMock,
) -> None:
    user_id = uuid4()
    mock_delivery_repo.count_pending_since = AsyncMock(return_value=100)
    allowed, reason = await rate_limiter.check_and_record(user_id, "email")
    assert allowed is False
    assert reason is not None
    assert len(reason) > 0


@pytest.mark.asyncio
async def test_users_cannot_disable_all_safety_limits(
    rate_limiter: NotificationRateLimiter,
    mock_delivery_repo: MagicMock,
) -> None:
    user_id = uuid4()
    mock_delivery_repo.count_pending_since = AsyncMock(return_value=999)
    allowed, reason = await rate_limiter.check_and_record(user_id, "email")
    assert allowed is False
    assert reason is not None


@pytest.mark.asyncio
async def test_get_user_daily_email_count(
    rate_limiter: NotificationRateLimiter,
    mock_delivery_repo: MagicMock,
) -> None:
    user_id = uuid4()
    mock_delivery_repo.count_pending_since = AsyncMock(return_value=7)
    count = await rate_limiter.get_user_daily_email_count(user_id)
    assert count == 7


@pytest.mark.asyncio
async def test_get_user_daily_notification_count_delegates(
    rate_limiter: NotificationRateLimiter,
    mock_delivery_repo: MagicMock,
) -> None:
    user_id = uuid4()
    mock_delivery_repo.count_pending_since = AsyncMock(return_value=4)
    count = await rate_limiter.get_user_daily_notification_count(user_id)
    assert count == 4


@pytest.mark.asyncio
async def test_get_user_daily_digest_count(
    rate_limiter: NotificationRateLimiter,
    mock_delivery_repo: MagicMock,
) -> None:
    user_id = uuid4()
    mock_delivery_repo.count_pending_since = AsyncMock(return_value=3)
    count = await rate_limiter.get_user_daily_digest_count(user_id)
    assert count == 3


__all__ = [
    "test_concurrent_access_does_not_bypass_caps",
    "test_daily_cap_enforcement_per_user",
    "test_digest_cap_enforcement",
    "test_email_cap_enforcement",
    "test_get_user_daily_digest_count",
    "test_get_user_daily_email_count",
    "test_get_user_daily_notification_count_delegates",
    "test_global_rate_limit_enforcement",
    "test_suppressed_notifications_have_recorded_reason",
    "test_users_cannot_disable_all_safety_limits",
    "test_within_caps_allows_delivery",
]
