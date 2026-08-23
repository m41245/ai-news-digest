"""Production smoke-test suite for Milestone 9."""

from __future__ import annotations

import sys
from typing import Any

import requests

BASE_URL = "http://localhost:8000"
API_PREFIX = f"{BASE_URL}/api/v1"


def smoke_test(name: str, fn: Any) -> bool:
    try:
        fn()
        print(f"[PASS] {name}")
        return True
    except Exception as exc:
        print(f"[FAIL] {name}: {exc}")
        return False


def test_liveness() -> None:
    resp = requests.get(f"{BASE_URL}/health/live", timeout=5)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert data["status"] == "alive"


def test_readiness() -> None:
    resp = requests.get(f"{BASE_URL}/health/ready", timeout=5)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["cache"] == "ok"


def test_register_and_login() -> tuple[str, str]:
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
        raise AssertionError(f"Register failed: {resp.status_code} {resp.text}")

    resp = requests.post(
        f"{API_PREFIX}/auth/login",
        json={"username": email, "password": password},
        timeout=5,
    )
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "access_token" in data, f"No access_token in response: {data}"
    return data["access_token"], email


def test_invalid_auth() -> None:
    resp = requests.get(
        f"{API_PREFIX}/articles/",
        headers={"Authorization": "Bearer invalid.token.here"},
        timeout=5,
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


def test_authorized_endpoint(token: str) -> None:
    resp = requests.get(
        f"{API_PREFIX}/articles/",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.text}"


def test_unauthorized_endpoint() -> None:
    resp = requests.get(f"{API_PREFIX}/admin/users", timeout=5)
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


def test_admin_endpoint(token: str) -> None:
    resp = requests.get(
        f"{API_PREFIX}/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    # Should be 403 because test user is not admin
    assert resp.status_code in (401, 403), f"Expected 401/403, got {resp.status_code}"


def test_metrics_endpoint(token: str) -> None:
    resp = requests.get(
        f"{BASE_URL}/metrics",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert resp.status_code in (200, 403), (
        f"Expected 200 or 403, got {resp.status_code}"
    )
    if resp.status_code == 200:
        assert "http_request_total" in resp.text or (
            "text/plain" in resp.headers.get("content-type", "")
        )


def test_database_operation(token: str) -> None:
    resp = requests.get(
        f"{API_PREFIX}/sources/",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.text}"
    data = resp.json()
    assert "items" in data or "total" in data or isinstance(data, list)


def test_redis_operation(token: str) -> None:
    resp = requests.get(
        f"{BASE_URL}/metrics/health",
        timeout=5,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"


def main() -> int:
    token = None

    results: list[bool] = []

    results.append(smoke_test("Liveness", test_liveness))
    results.append(smoke_test("Readiness", test_readiness))

    try:
        token, _ = test_register_and_login()
    except Exception as exc:
        print(f"[FAIL] Register/Login: {exc}")
        results.append(False)
        token = None

    if token:
        results.append(smoke_test("Invalid Authentication", lambda: test_invalid_auth()))
        results.append(smoke_test("Authorized Endpoint", lambda: test_authorized_endpoint(token)))
        results.append(smoke_test("Unauthorized Endpoint", test_unauthorized_endpoint))
        results.append(
            smoke_test("Admin-only Endpoint", lambda: test_admin_endpoint(token))
        )
        results.append(
            smoke_test("Metrics Endpoint", lambda: test_metrics_endpoint(token))
        )
        results.append(
            smoke_test(
                "Database-backed Operation", lambda: test_database_operation(token)
            )
        )
        results.append(
            smoke_test(
                "Redis-backed Operation", lambda: test_redis_operation(token)
            )
        )

    passed = sum(results)
    total = len(results)
    print(f"\nSmoke tests: {passed}/{total} passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
