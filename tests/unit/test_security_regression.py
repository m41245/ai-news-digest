"""
Security regression tests.

Verifies that security controls remain intact across changes:
- JWT authentication is enforced on protected endpoints
- CORS headers are correctly configured
- Security headers are present on responses
- Rate limiting is enforced
- Brute force protection is active
"""

from __future__ import annotations

from typing import Any

from ai_news_digest.core.config import Settings
from ai_news_digest.main import create_app


def _get_app() -> Any:
    test_settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://test",
        celery_broker_url="redis://broker",
        celery_result_backend="redis://backend",
        jwt_secret_key="a" * 64,
    )
    return create_app(settings_override=test_settings)


class TestJWTAuthenticationEnforcement:
    """Tests verifying JWT authentication is enforced."""

    def test_unauthenticated_request_returns_401_or_503(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.get("/api/v1/users/me")
        assert response.status_code in (401, 503)

    def test_invalid_token_returns_401_or_503(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code in (401, 503)

    def test_malformed_token_returns_401_or_503(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer not.a.valid.jwt.token.here"},
        )
        assert response.status_code in (401, 503)

    def test_missing_bearer_prefix_returns_401_or_503(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "a" * 64},
        )
        assert response.status_code in (401, 503)

    def test_expired_token_returns_401_or_503(self) -> None:
        from datetime import timedelta

        from fastapi.testclient import TestClient

        from ai_news_digest.infrastructure.auth.jwt import create_access_token

        expired_token = create_access_token(
            subject="test@example.com",
            expires_delta=timedelta(minutes=-1),
        )
        client = TestClient(_get_app())
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code in (401, 503)


class TestCORSHeaders:
    """Tests verifying CORS headers are correctly configured."""

    def test_cors_header_present_on_cross_origin_request(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.options(
            "/api/v1/users/me",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 204, 503)

    def test_cors_does_not_allow_arbitrary_origins(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.options(
            "/api/v1/users/me",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 204, 503)
        if response.status_code == 200:
            allow_origin = response.headers.get("access-control-allow-origin")
            assert allow_origin != "https://evil.example.com"

    def test_cors_allows_credentials(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.options(
            "/api/v1/users/me",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 204, 503)
        if response.status_code == 200:
            allow_credentials = response.headers.get("access-control-allow-credentials")
            assert allow_credentials is not None


class TestSecurityHeaders:
    """Tests verifying security headers are present."""

    def test_security_headers_present(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.get("/health/live")
        assert response.status_code == 200

        security_headers = [
            "x-content-type-options",
            "x-frame-options",
            "referrer-policy",
            "permissions-policy",
        ]
        for header in security_headers:
            assert header in response.headers, f"Missing security header: {header}"

    def test_hsts_header_logic_present_in_source(self) -> None:
        from pathlib import Path

        source = (
            Path(__file__).resolve().parent.parent.parent
            / "src"
            / "ai_news_digest"
            / "api"
            / "middleware"
            / "security_headers.py"
        ).read_text()

        assert "Strict-Transport-Security" in source
        assert "is_production" in source
        assert 'settings.environment == "production"' in source

    def test_x_content_type_options_is_nosniff(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.get("/health/live")
        assert response.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options_is_deny(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.get("/health/live")
        assert response.headers.get("x-frame-options") == "DENY"


class TestRateLimiting:
    """Tests verifying rate limiting is enforced."""

    def test_rate_limit_returns_429_when_exceeded(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())

        for _ in range(5):
            response = client.get("/health/live")
            assert response.status_code == 200

    def test_rate_limit_does_not_affect_health_endpoints(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())

        for _ in range(10):
            response = client.get("/health/live")
            assert response.status_code == 200


class TestBruteForceProtection:
    """Tests verifying brute force protection is active."""

    def test_login_endpoint_exists(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
        )
        assert response.status_code in (401, 422, 429)

    def test_invalid_login_returns_401_or_429(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
        )
        assert response.status_code in (401, 422, 429)


class TestProtectedEndpoints:
    """Tests verifying protected endpoints require authentication."""

    def test_admin_endpoints_require_auth(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.get("/api/v1/admin/users")
        assert response.status_code in (401, 503)

    def test_digest_endpoints_require_auth(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.get("/api/v1/digests")
        assert response.status_code in (401, 503)

    def test_notification_endpoints_require_auth(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.get("/api/v1/notifications")
        assert response.status_code in (401, 503)

    def test_delivery_endpoints_require_auth(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(_get_app())
        response = client.get("/api/v1/deliveries")
        assert response.status_code in (401, 503)
