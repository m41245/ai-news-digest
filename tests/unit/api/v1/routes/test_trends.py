"""
Unit tests for M85 public trend API routes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.public import router
from ai_news_digest.domain.enums.trend_status import TrendStatus
from ai_news_digest.domain.enums.trend_type import TrendType
from ai_news_digest.domain.models.trend import Trend


def _make_trend(trend_id: uuid4 | None = None) -> Trend:
    now = datetime.now(UTC)
    return Trend(
        id=trend_id or uuid4(),
        trend_type=TrendType.COMPANY_TREND,
        canonical_key="company:openai",
        display_name="OpenAI",
        status=TrendStatus.EMERGING,
        trend_score=75.0,
        momentum_score=80.0,
        first_detected_at=now - timedelta(days=1),
        last_detected_at=now,
        recent_activity=14,
        baseline_activity=8,
        source_count=7,
        story_count=4,
        event_count=2,
        explanation="recent=14; baseline=8; growth=+0.75; sources=7",
    )


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    container.trend_repository = AsyncMock()
    return container


def test_list_trends_returns_paginated(mock_container: MagicMock) -> None:
    mock_container.trend_repository.list_public.return_value = [_make_trend()]
    mock_container.trend_repository.count_public.return_value = 1

    app = MagicMock()
    app.dependency_overrides = {}
    from fastapi import FastAPI
    from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers

    api = FastAPI()
    setup_exception_handlers(api)
    api.include_router(router)

    api.dependency_overrides[get_container] = lambda: mock_container

    client = TestClient(api)
    response = client.get("/public/trends")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["display_name"] == "OpenAI"


def test_get_trend_by_id_returns_trend(mock_container: MagicMock) -> None:
    trend = _make_trend()
    mock_container.trend_repository.get_by_id.return_value = trend

    app = MagicMock()
    from fastapi import FastAPI
    from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers

    api = FastAPI()
    setup_exception_handlers(api)
    api.include_router(router)

    api.dependency_overrides[get_container] = lambda: mock_container

    client = TestClient(api)
    response = client.get(f"/public/trends/{trend.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "OpenAI"
    assert data["trend_type"] == "company_trend"


def test_get_trend_not_found(mock_container: MagicMock) -> None:
    mock_container.trend_repository.get_by_id.return_value = None

    app = MagicMock()
    from fastapi import FastAPI
    from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers

    api = FastAPI()
    setup_exception_handlers(api)
    api.include_router(router)

    api.dependency_overrides[get_container] = lambda: mock_container

    client = TestClient(api)
    response = client.get(f"/public/trends/{uuid4()}")
    assert response.status_code == 404


__all__ = [
    "test_get_trend_by_id_returns_trend",
    "test_get_trend_not_found",
    "test_list_trends_returns_paginated",
]
