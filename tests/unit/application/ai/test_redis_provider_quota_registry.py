"""
Unit tests for M79 Redis provider quota registry.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import RedisError

from ai_news_digest.application.ai.quota import (
    ProviderQuotaConfig,
    ProviderUsage,
    QuotaLimit,
    QuotaWindow,
)
from ai_news_digest.infrastructure.quota.redis_provider_quota_registry import (
    RedisProviderQuotaRegistry,
    _provider_quota_key,
    _provider_usage_key,
    _window_id,
)


@pytest.fixture
def quota_registry() -> RedisProviderQuotaRegistry:
    return RedisProviderQuotaRegistry(redis_url="redis://localhost:6379/0")


def test_window_id_minute() -> None:
    dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
    assert _window_id(QuotaWindow.MINUTE, dt) == "202401151030"


def test_window_id_hour() -> None:
    dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
    assert _window_id(QuotaWindow.HOUR, dt) == "2024011510"


def test_window_id_day() -> None:
    dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
    assert _window_id(QuotaWindow.DAY, dt) == "20240115"


def test_window_id_month() -> None:
    dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
    assert _window_id(QuotaWindow.MONTH, dt) == "202401"


def test_provider_quota_key() -> None:
    assert _provider_quota_key("openai") == "ai:provider-quota:openai"


def test_provider_usage_key() -> None:
    assert _provider_usage_key("openai", QuotaWindow.DAY) == "ai:provider-quota:openai:usage:day"


@pytest.mark.asyncio
async def test_get_provider_quota_returns_none_when_absent(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {}
    quota_registry._client = mock_client

    result = await quota_registry.get_provider_quota("openai")
    assert result is None


@pytest.mark.asyncio
async def test_set_and_get_provider_quota(quota_registry: RedisProviderQuotaRegistry) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {}
    quota_registry._client = mock_client

    config = ProviderQuotaConfig(
        provider_id="openai",
        limits=[
            QuotaLimit(window=QuotaWindow.DAY, request_limit=100, token_limit=10000),
        ],
    )
    await quota_registry.set_provider_quota(config)

    mock_client.hset.assert_called_once()
    mock_client.expire.assert_called_once()

    mock_client.hgetall.return_value = {
        "provider_id": "openai",
        "limits": json.dumps([
            {"window": "day", "request_limit": 100, "token_limit": 10000, "cost_limit": None}
        ]),
    }
    result = await quota_registry.get_provider_quota("openai")
    assert result is not None
    assert result.provider_id == "openai"
    assert len(result.limits) == 1
    assert result.limits[0].request_limit == 100


@pytest.mark.asyncio
async def test_record_usage_success(quota_registry: RedisProviderQuotaRegistry) -> None:
    mock_client = AsyncMock()
    mock_client.eval.return_value = []
    quota_registry._client = mock_client

    usage = ProviderUsage(
        provider_id="openai",
        request_count=1,
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        estimated_cost=Decimal("0.01"),
        window=QuotaWindow.DAY,
    )
    await quota_registry.record_usage(usage)

    mock_client.eval.assert_called_once()


@pytest.mark.asyncio
async def test_check_quota_eligible_when_no_limits(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {}
    quota_registry._client = mock_client

    result = await quota_registry.check_quota_eligibility("openai", QuotaWindow.DAY)
    assert result.eligible is True
    assert result.reason == "no_quota_configured"


@pytest.mark.asyncio
async def test_check_quota_eligible_when_under_limit(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {}
    mock_client.eval.return_value = "eligible"
    quota_registry._client = mock_client

    config = ProviderQuotaConfig(
        provider_id="openai",
        limits=[
            QuotaLimit(
                window=QuotaWindow.DAY,
                request_limit=100,
                token_limit=10000,
                cost_limit=Decimal("5.0"),
            )
        ],
    )
    await quota_registry.set_provider_quota(config)

    mock_client.hgetall.return_value = {
        "provider_id": "openai",
        "limits": json.dumps([
            {"window": "day", "request_limit": 100, "token_limit": 10000, "cost_limit": "5.0"}
        ]),
    }
    result = await quota_registry.check_quota_eligibility(
        "openai", QuotaWindow.DAY, estimated_tokens=100, estimated_cost=0.1
    )
    assert result.eligible is True
    assert result.reason == "eligible"


@pytest.mark.asyncio
async def test_check_quota_excluded_when_request_limit_exhausted(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {
        "provider_id": "openai",
        "limits": json.dumps([
            {"window": "day", "request_limit": 100, "token_limit": 10000, "cost_limit": "5.0"}
        ]),
    }
    mock_client.eval.return_value = "request_exhausted"
    quota_registry._client = mock_client

    result = await quota_registry.check_quota_eligibility(
        "openai", QuotaWindow.DAY, estimated_tokens=100, estimated_cost=0.1
    )
    assert result.eligible is False
    assert result.reason == "request_quota_exhausted"


@pytest.mark.asyncio
async def test_get_global_budget_defaults(quota_registry: RedisProviderQuotaRegistry) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {}
    quota_registry._client = mock_client

    result = await quota_registry.get_global_budget()
    assert result.daily_budget == Decimal("0")
    assert result.monthly_budget == Decimal("0")


@pytest.mark.asyncio
async def test_update_global_budget(quota_registry: RedisProviderQuotaRegistry) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {
        "daily_budget": "10.0",
        "monthly_budget": "100.0",
        "daily_spend": "0.0",
        "monthly_spend": "0.0",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    quota_registry._client = mock_client

    result = await quota_registry.update_global_budget(1.5)
    assert result.daily_spend == Decimal("1.5")
    assert result.monthly_spend == Decimal("1.5")


@pytest.mark.asyncio
async def test_redis_error_handled_gracefully(quota_registry: RedisProviderQuotaRegistry) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.side_effect = RedisError("connection lost")
    quota_registry._client = mock_client

    result = await quota_registry.get_provider_quota("openai")
    assert result is None

    result = await quota_registry.check_quota_eligibility("openai", QuotaWindow.DAY)
    assert result.eligible is True
    assert result.reason == "no_quota_configured"
