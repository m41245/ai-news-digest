"""
Unit tests for health API routes.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.api.v1.routes.health import router


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the health router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    """Test basic health endpoint."""
    response = client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "application" in data


def test_readiness_endpoint(client: TestClient) -> None:
    """Test readiness endpoint."""
    response = client.get("/health/ready")

    assert response.status_code in (200, 503)
    data = response.json()
    assert data["status"] in ("ready", "degraded")
    assert "checks" in data
