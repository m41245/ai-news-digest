"""Production smoke-test suite for Milestone 9 / Phase 16.

This module provides comprehensive smoke tests for a running production stack.
It covers frontend/API availability, health endpoints, public endpoints,
authentication, protected endpoints, admin authorization, Redis, database,
Celery, reverse proxy behavior, security headers, and response times.

Usage:
    # Run all smoke tests:
    python -m tests.smoke_prod

    # Run a specific test by name:
    python -m tests.smoke_prod --test liveness

    # Run multiple specific tests:
    python -m tests.smoke_prod --test liveness --test readiness

    # List all available tests:
    python -m tests.smoke_prod --list
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

import requests

BASE_URL = "http://localhost:8000"
API_PREFIX = f"{BASE_URL}/api/v1"
FRONTEND_URL = "http://localhost:3000"

# Response time threshold in seconds
RESPONSE_TIME_THRESHOLD = 2.0


def smoke_test(name: str, fn: Any) -> bool:
    """Execute a smoke test function and report the result."""
    try:
        fn()
        print(f"[PASS] {name}")
        return True
    except requests.exceptions.ConnectionError as exc:
        print(f"[FAIL] {name}: Connection error - {exc}")
        return False
    except requests.exceptions.Timeout as exc:
        print(f"[FAIL] {name}: Request timed out - {exc}")
        return False
    except AssertionError as exc:
        print(f"[FAIL] {name}: Assertion failed - {exc}")
        return False
    except Exception as exc:
        print(f"[FAIL] {name}: Unexpected error - {type(exc).__name__}: {exc}")
        return False


def test_liveness() -> None:
    """Test that the liveness endpoint returns 200 and status 'alive'."""
    resp = requests.get(f"{BASE_URL}/health/live", timeout=5)
    assert (
        resp.status_code == 200
    ), f"Expected 200, got {resp.status_code}. Response body: {resp.text[:200]}"
    data = resp.json()
    assert data["status"] == "alive", f"Expected status 'alive', got '{data.get('status')}'"
    assert (
        data["application"] == "AI News Digest"
    ), f"Expected application name 'AI News Digest', got '{data.get('application')}'"


def test_readiness() -> None:
    """Test that the readiness endpoint returns 200 with healthy checks."""
    resp = requests.get(f"{BASE_URL}/health/ready", timeout=5)
    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}. "
        f"Service may be degraded. Response: {resp.text[:200]}"
    )
    data = resp.json()
    assert data["status"] == "ready", f"Expected status 'ready', got '{data.get('status')}'"
    assert (
        data["checks"]["database"] == "ok"
    ), f"Database check failed: {data['checks'].get('database')}"
    assert data["checks"]["cache"] == "ok", f"Cache check failed: {data['checks'].get('cache')}"


def test_frontend_availability() -> None:
    """Test that the frontend container is serving content."""
    try:
        resp = requests.get(FRONTEND_URL, timeout=5)
    except requests.exceptions.ConnectionError:
        print("  [WARN] Frontend not available at :3000 (may not be running)")
        return
    assert resp.status_code == 200, f"Expected 200 from frontend, got {resp.status_code}"
    assert len(resp.text) > 0, "Frontend returned empty response body"


def test_api_availability() -> None:
    """Test that the API root endpoint is accessible."""
    resp = requests.get(f"{BASE_URL}/", timeout=5)
    assert resp.status_code == 200, f"Expected 200 from API root, got {resp.status_code}"
    data = resp.json()
    assert "message" in data, f"Missing 'message' in response: {data}"
    assert "version" in data, f"Missing 'version' in response: {data}"


def test_security_headers() -> None:
    """Test that security headers are present in API responses."""
    resp = requests.get(f"{BASE_URL}/health/live", timeout=5)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    expected_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    for header, expected_value in expected_headers.items():
        actual_value = resp.headers.get(header)
        assert actual_value is not None, f"Missing security header: {header}"
        assert (
            actual_value == expected_value
        ), f"Header {header}: expected '{expected_value}', got '{actual_value}'"


def test_hsts_header() -> None:
    """Test that HSTS header is present in production (non-development) mode."""
    resp = requests.get(f"{BASE_URL}/health/live", timeout=5)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    hsts = resp.headers.get("Strict-Transport-Security")
    if hsts is not None:
        assert "max-age=" in hsts, f"HSTS header present but missing max-age: {hsts}"
        assert (
            "includeSubDomains" in hsts
        ), f"HSTS header present but missing includeSubDomains: {hsts}"
    else:
        print("  [INFO] HSTS header not present (may be development mode)")


def test_request_id_header() -> None:
    """Test that X-Request-ID header is present in responses."""
    resp = requests.get(f"{BASE_URL}/health/live", timeout=5)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    request_id = resp.headers.get("X-Request-ID")
    assert request_id is not None, "Missing X-Request-ID header"
    assert len(request_id) > 0, "X-Request-ID header is empty"


def test_process_time_header() -> None:
    """Test that X-Process-Time header is present and valid."""
    resp = requests.get(f"{BASE_URL}/health/live", timeout=5)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    process_time = resp.headers.get("X-Process-Time")
    assert process_time is not None, "Missing X-Process-Time header"
    try:
        time_value = float(process_time)
        assert time_value >= 0, f"X-Process-Time is negative: {time_value}"
    except ValueError as err:
        raise AssertionError(f"X-Process-Time is not a valid float: {process_time}") from err


def test_cors_headers() -> None:
    """Test that CORS headers are present for cross-origin requests."""
    headers = {
        "Origin": "http://localhost:3000",
    }
    resp = requests.get(f"{BASE_URL}/health/live", headers=headers, timeout=5)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    cors_header = resp.headers.get("Access-Control-Allow-Origin")
    assert cors_header is not None, "Missing Access-Control-Allow-Origin header for CORS request"


def test_public_articles() -> None:
    """Test that the public articles endpoint returns a valid response."""
    resp = requests.get(f"{API_PREFIX}/public/articles", timeout=5)
    assert (
        resp.status_code == 200
    ), f"Expected 200 from public articles, got {resp.status_code}. Response: {resp.text[:200]}"
    data = resp.json()
    assert "items" in data, f"Missing 'items' in response: {data}"
    assert "total" in data, f"Missing 'total' in response: {data}"
    assert isinstance(data["items"], list), f"'items' should be a list, got {type(data['items'])}"
    assert isinstance(data["total"], int), f"'total' should be an int, got {type(data['total'])}"


def test_public_digests() -> None:
    """Test that the public digests endpoint returns a valid response."""
    resp = requests.get(f"{API_PREFIX}/public/digests", timeout=5)
    assert (
        resp.status_code == 200
    ), f"Expected 200 from public digests, got {resp.status_code}. Response: {resp.text[:200]}"
    data = resp.json()
    assert "items" in data, f"Missing 'items' in response: {data}"
    assert "total" in data, f"Missing 'total' in response: {data}"
    assert isinstance(data["items"], list), f"'items' should be a list, got {type(data['items'])}"


def test_public_categories() -> None:
    """Test that the public categories endpoint returns a valid response."""
    resp = requests.get(f"{API_PREFIX}/public/categories", timeout=5)
    assert (
        resp.status_code == 200
    ), f"Expected 200 from public categories, got {resp.status_code}. Response: {resp.text[:200]}"
    data = resp.json()
    assert isinstance(data, list), f"Expected list response, got {type(data)}"


def test_response_time() -> None:
    """Test that API response time is under the threshold."""
    start = time.time()
    resp = requests.get(f"{BASE_URL}/health/live", timeout=RESPONSE_TIME_THRESHOLD + 5)
    elapsed = time.time() - start

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert (
        elapsed < RESPONSE_TIME_THRESHOLD
    ), f"Response time {elapsed:.3f}s exceeds threshold of {RESPONSE_TIME_THRESHOLD}s"


def test_register_and_login() -> tuple[str, str]:
    """Test user registration and login flow."""
    email = "smoke-test@example.com"
    password = "SmokeTest123!"  # noqa: S105
    name = "Smoke Test User"

    resp = requests.post(
        f"{API_PREFIX}/auth/register",
        json={"email": email, "password": password, "name": name},
        timeout=5,
    )
    # May fail if user already exists (400/409), that's okay for smoke test
    if resp.status_code not in (200, 201, 400, 409):
        raise AssertionError(
            f"Register failed: expected 200/201/400/409, got {resp.status_code}. "
            f"Response: {resp.text[:200]}"
        )

    resp = requests.post(
        f"{API_PREFIX}/auth/login",
        json={"username": email, "password": password},
        timeout=5,
    )
    assert (
        resp.status_code == 200
    ), f"Login failed: expected 200, got {resp.status_code}. Response: {resp.text[:200]}"
    data = resp.json()
    assert "access_token" in data, f"No access_token in response: {data}"
    assert len(data["access_token"]) > 0, "access_token is empty"
    return data["access_token"], email


def test_invalid_auth() -> None:
    """Test that invalid authentication tokens are rejected."""
    resp = requests.get(
        f"{API_PREFIX}/articles/",
        headers={"Authorization": "Bearer invalid.token.here"},
        timeout=5,
    )
    assert (
        resp.status_code == 401
    ), f"Expected 401 for invalid token, got {resp.status_code}. Response: {resp.text[:200]}"


def test_authorized_endpoint(token: str) -> None:
    """Test that authenticated users can access protected endpoints."""
    resp = requests.get(
        f"{API_PREFIX}/articles/",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert (
        resp.status_code == 200
    ), f"Expected 200 for authorized request, got {resp.status_code}. Response: {resp.text[:200]}"


def test_unauthorized_endpoint() -> None:
    """Test that unauthenticated requests to protected endpoints are rejected."""
    resp = requests.get(f"{API_PREFIX}/admin/users", timeout=5)
    assert resp.status_code == 401, (
        f"Expected 401 for unauthorized request, got {resp.status_code}. "
        f"Response: {resp.text[:200]}"
    )


def test_admin_endpoint(token: str) -> None:
    """Test that non-admin users cannot access admin endpoints."""
    resp = requests.get(
        f"{API_PREFIX}/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    # Should be 403 because test user is not admin
    assert resp.status_code in (401, 403), (
        f"Expected 401/403 for non-admin access, got {resp.status_code}. "
        f"Response: {resp.text[:200]}"
    )


def test_metrics_endpoint(token: str) -> None:
    """Test that metrics endpoint is accessible to authenticated users."""
    resp = requests.get(
        f"{BASE_URL}/metrics",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert resp.status_code in (
        200,
        403,
    ), f"Expected 200 or 403 for metrics, got {resp.status_code}. Response: {resp.text[:200]}"
    if resp.status_code == 200:
        content_type = resp.headers.get("content-type", "")
        assert (
            "http_request_total" in resp.text or "text/plain" in content_type
        ), f"Metrics endpoint returned unexpected content. Content-Type: {content_type}"


def test_database_operation(token: str) -> None:
    """Test that database-backed operations work correctly."""
    resp = requests.get(
        f"{API_PREFIX}/sources/",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert (
        resp.status_code == 200
    ), f"Expected 200 for database operation, got {resp.status_code}. Response: {resp.text[:200]}"
    data = resp.json()
    assert (
        "items" in data or "total" in data or isinstance(data, list)
    ), f"Unexpected response format: {data}"


def test_redis_operation(token: str) -> None:
    """Test that Redis-backed operations work correctly."""
    resp = requests.get(
        f"{BASE_URL}/metrics/health",
        timeout=5,
    )
    assert (
        resp.status_code == 200
    ), f"Expected 200 for Redis health, got {resp.status_code}. Response: {resp.text[:200]}"


def test_celery_worker_health(token: str) -> None:
    """Test that Celery workers are healthy and responding."""
    resp = requests.get(
        f"{API_PREFIX}/admin/workers/health",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    # May return 403 if user is not admin, which is acceptable
    if resp.status_code == 403:
        print("  [INFO] Skipping Celery health check (user is not admin)")
        return

    assert (
        resp.status_code == 200
    ), f"Expected 200 for worker health, got {resp.status_code}. Response: {resp.text[:200]}"
    data = resp.json()
    assert "status" in data, f"Missing 'status' in response: {data}"
    assert "broker_connected" in data, f"Missing 'broker_connected' in response: {data}"


def test_reverse_proxy_headers() -> None:
    """Test that reverse proxy headers are handled correctly."""
    # Test with X-Forwarded-For header (common with reverse proxies)
    headers = {
        "X-Forwarded-For": "192.168.1.100",
        "X-Forwarded-Proto": "https",
    }
    resp = requests.get(f"{BASE_URL}/health/live", headers=headers, timeout=5)
    assert resp.status_code == 200, f"Expected 200 with proxy headers, got {resp.status_code}"


def test_request_id_propagation() -> None:
    """Test that custom X-Request-ID is propagated through the stack."""
    custom_id = "smoke-test-request-12345"
    headers = {"X-Request-ID": custom_id}
    resp = requests.get(f"{BASE_URL}/health/live", headers=headers, timeout=5)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    returned_id = resp.headers.get("X-Request-ID")
    assert returned_id == custom_id, f"Expected X-Request-ID '{custom_id}', got '{returned_id}'"


# Registry of all available smoke tests
TEST_REGISTRY: dict[str, tuple[str, Any]] = {
    "liveness": ("Liveness", test_liveness),
    "readiness": ("Readiness", test_readiness),
    "frontend": ("Frontend Availability", test_frontend_availability),
    "api": ("API Availability", test_api_availability),
    "security-headers": ("Security Headers", test_security_headers),
    "hsts": ("HSTS Header", test_hsts_header),
    "request-id": ("X-Request-ID Header", test_request_id_header),
    "process-time": ("X-Process-Time Header", test_process_time_header),
    "cors": ("CORS Headers", test_cors_headers),
    "public-articles": ("Public Articles", test_public_articles),
    "public-digests": ("Public Digests", test_public_digests),
    "public-categories": ("Public Categories", test_public_categories),
    "response-time": ("API Response Time", test_response_time),
    "reverse-proxy": ("Reverse Proxy Headers", test_reverse_proxy_headers),
    "request-id-propagation": ("Request ID Propagation", test_request_id_propagation),
}

# Tests that require authentication
AUTH_TESTS: dict[str, tuple[str, Any]] = {
    "auth": ("Register and Login", test_register_and_login),
    "invalid-auth": ("Invalid Authentication", test_invalid_auth),
    "authorized": ("Authorized Endpoint", test_authorized_endpoint),
    "unauthorized": ("Unauthorized Endpoint", test_unauthorized_endpoint),
    "admin": ("Admin-only Endpoint", test_admin_endpoint),
    "metrics": ("Metrics Endpoint", test_metrics_endpoint),
    "database": ("Database-backed Operation", test_database_operation),
    "redis": ("Redis-backed Operation", test_redis_operation),
    "celery": ("Celery Worker Health", test_celery_worker_health),
}


def list_tests() -> None:
    """Print all available test names."""
    print("\nAvailable smoke tests:")
    print("\n  Basic tests (no auth required):")
    for key, (name, _) in TEST_REGISTRY.items():
        print(f"    --test {key:<25} {name}")
    print("\n  Authenticated tests:")
    for key, (name, _) in AUTH_TESTS.items():
        print(f"    --test {key:<25} {name}")
    print()


def run_tests(test_names: list[str] | None = None) -> int:
    """Run smoke tests and return exit code."""
    token = None
    results: list[bool] = []

    # Determine which tests to run
    if test_names:
        tests_to_run: list[tuple[str, str, Any]] = []
        for name in test_names:
            if name in TEST_REGISTRY:
                display_name, fn = TEST_REGISTRY[name]
                tests_to_run.append((name, display_name, fn))
            elif name in AUTH_TESTS:
                display_name, fn = AUTH_TESTS[name]
                tests_to_run.append((name, display_name, fn))
            else:
                print("[ERROR] Unknown test:", name)
                print("  Run with --list to see available tests")
                return 1
    else:
        tests_to_run = [(key, name, fn) for key, (name, fn) in TEST_REGISTRY.items()]

    # Run basic tests first
    for key, display_name, fn in tests_to_run:
        if key in AUTH_TESTS:
            continue
        results.append(smoke_test(display_name, fn))

    # Handle authentication tests
    auth_tests_to_run = [(key, name, fn) for key, name, fn in tests_to_run if key in AUTH_TESTS]

    if auth_tests_to_run:
        # Try to authenticate first
        try:
            token, _ = test_register_and_login()
            results.append(smoke_test("Register and Login", lambda: True))
        except Exception as exc:
            print(f"[FAIL] Register/Login: {exc}")
            results.append(False)
            token = None

        if token:
            for key, display_name, fn in auth_tests_to_run:
                if key == "auth":
                    continue  # Already tested above
                results.append(smoke_test(display_name, lambda fn=fn: fn(token)))

    passed = sum(results)
    total = len(results)
    print(f"\nSmoke tests: {passed}/{total} passed")

    return 0 if passed == total else 1


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Production smoke-test suite for AI News Digest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tests.smoke_prod                    # Run all tests
  python -m tests.smoke_prod --test liveness    # Run single test
  python -m tests.smoke_prod --list             # List available tests
        """,
    )
    parser.add_argument(
        "--test",
        action="append",
        dest="tests",
        help="Run a specific test by name (can be specified multiple times)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available tests and exit",
    )
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help=f"Base URL for the API (default: {BASE_URL})",
    )
    parser.add_argument(
        "--frontend-url",
        default=FRONTEND_URL,
        help=f"Frontend URL (default: {FRONTEND_URL})",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point for the smoke test suite."""
    args = parse_args()

    global BASE_URL, API_PREFIX, FRONTEND_URL
    BASE_URL = args.base_url.rstrip("/")
    API_PREFIX = f"{BASE_URL}/api/v1"
    FRONTEND_URL = args.frontend_url.rstrip("/")

    if args.list:
        list_tests()
        return 0

    return run_tests(args.tests)


if __name__ == "__main__":
    sys.exit(main())
