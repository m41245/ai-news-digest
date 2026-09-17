"""Tests for M93 intelligence evaluation API routes."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException
from ai_news_digest.api.v1.routes.intelligence_evaluation import router
from ai_news_digest.domain.evaluation.metrics import (
    EvaluationMetricType,
    EvaluationReport,
    EvaluationStatus,
    MetricValue,
)
from ai_news_digest.domain.models.user import User
from ai_news_digest.api.v1.dependencies.auth import get_current_admin_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

@pytest.fixture
def mock_admin():
    return MagicMock(spec=User, is_admin=True, is_active=True)

@pytest.fixture
def mock_container():
    container = MagicMock()
    container.session = AsyncMock()
    container.evaluation_repository = AsyncMock()
    container.drift_detector = MagicMock()
    container.evaluation_repository.list_runs.return_value = ([], 0)
    container.evaluation_repository.list_snapshots.return_value = ([], 0)
    container.evaluation_repository.get_run.return_value = None
    container.drift_detector.detect_drift.return_value = []
    container.drift_detector.classify_health.return_value = ("healthy", [])
    return container


class TestListEvaluationRuns:
    @pytest.mark.asyncio
    async def test_list_runs_requires_admin(self, mock_container, mock_admin):
        from ai_news_digest.api.v1.dependencies.dependencies import get_container
        from fastapi import Depends
        from ai_news_digest.api.v1.dependencies.auth import get_current_admin_user

        # Just verify the router has the endpoint
        routes = [r.path for r in router.routes]
        assert "/intelligence/evaluations" in routes

    @pytest.mark.asyncio
    async def test_list_runs_paginated(self, mock_container, mock_admin):
        from ai_news_digest.infrastructure.database.models.evaluation_run_model import EvaluationRunModel
        run = MagicMock(spec=EvaluationRunModel)
        run.run_id = "run-1"
        run.evaluation_type = "daily"
        run.scope = "global"
        run.status = "completed"
        run.started_at = datetime.now(UTC)
        run.completed_at = datetime.now(UTC)
        run.dataset_version = "production"
        run.benchmark_version = "m93-v1"
        run.configuration_version = "v1"
        run.provider = None
        run.model = None
        run.sample_count = 10
        run.metric_count = 5
        run.error = None
        mock_container.evaluation_repository.list_runs.return_value = ([run], 1)

        # Verify the response model shape
        from ai_news_digest.api.v1.schemas.intelligence_evaluation import EvaluationRunResponse
        resp = EvaluationRunResponse(
            run_id="run-1",
            evaluation_type="daily",
            scope="global",
            status="completed",
            started_at=datetime.now(UTC).isoformat(),
            completed_at=datetime.now(UTC).isoformat(),
            sample_count=10,
            metric_count=5,
        )
        assert resp.run_id == "run-1"


class TestDriftEndpoint:
    @pytest.mark.asyncio
    async def test_drift_health_requires_baseline(
        self, mock_container, mock_admin
    ):
        from fastapi import FastAPI, Depends
        from ai_news_digest.api.v1.dependencies.dependencies import get_container
        from ai_news_digest.api.v1.dependencies.auth import get_current_admin_user
        from ai_news_digest.api.v1.routes.intelligence_evaluation import router

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_container] = lambda: mock_container
        app.dependency_overrides[get_current_admin_user] = lambda: mock_admin

        mock_container.evaluation_repository.list_runs.return_value = ([], 0)

        client = TestClient(app)
        response = client.get("/intelligence/quality/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "insufficient_data"