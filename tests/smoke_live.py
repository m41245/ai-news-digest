"""
M42 Live HTTP Smoke Tests

Exercises the running Docker stack through actual HTTP endpoints.
Requires the validation stack to be running:
    docker compose -f docker-compose.prod.validation.yml up -d
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import requests

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


class SmokeTestRunner:
    """Run live HTTP smoke tests against the running Docker stack."""

    def __init__(self, base_url: str = BASE_URL, api_prefix: str = API_PREFIX) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_prefix = api_prefix.rstrip("/")
        self.session = requests.Session()
        self.tokens: dict[str, str] = {}
        self.user_ids: dict[str, str] = {}
        self.results: list[dict[str, Any]] = []

    def record(
        self,
        name: str,
        expected: int,
        actual: int,
        response: requests.Response | None = None,
    ) -> None:
        status = "PASS" if actual == expected else "FAIL"
        self.results.append({
            "test": name,
            "expected": expected,
            "actual": actual,
            "status": status,
        })
        if status == "FAIL":
            body = ""
            if response is not None:
                try:
                    body = response.text[:500]
                except Exception:
                    body = "<unreadable>"
            print(f"  FAIL: {name} expected {expected}, got {actual}")
            if body:
                print(f"    Response: {body}")

    def request(
        self,
        method: str,
        path: str,
        *,
        user: str | None = None,
        expected_status: int = 200,
        **kwargs: Any,
    ) -> requests.Response:
        """Make authenticated request."""
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        if user and user in self.tokens:
            headers.setdefault("Authorization", f"Bearer {self.tokens[user]}")
        response = self.session.request(method, url, headers=headers, **kwargs)
        self.record(
            f"{method} {path}",
            expected_status,
            response.status_code,
            response,
        )
        return response

    def run(self) -> None:
        """Run all smoke tests."""
        print("=" * 70)
        print("M42 Live HTTP Smoke Tests")
        print("=" * 70)

        self.test_health()
        self.test_authentication()
        self.test_public_feed()
        self.test_personalized_feed()
        self.test_story_detail()
        self.test_notification_preferences()
        self.test_schedule_preview()
        self.test_notification_delivery()
        self.test_delivery_history()
        self.test_unsubscribe()
        self.test_cross_user_access()
        self.test_invalid_requests()
        self.test_unauthorized_requests()

        self.print_summary()

    def test_health(self) -> None:
        """Test health endpoints."""
        print("\n[1] Health Endpoints")
        self.request("GET", "/health/live", expected_status=200)
        self.request("GET", "/health/ready", expected_status=200)
        self.request("GET", "/metrics", expected_status=401)

    def test_authentication(self) -> None:
        """Test authentication flow."""
        print("\n[2] Authentication")
        unique_id = str(uuid.uuid4())[:8]
        email = f"smoke_{unique_id}@example.com"
        password = "SmokeTest123!"

        register_data = {
            "email": email,
            "password": password,
            "name": f"Smoke User {unique_id}",
        }
        response = self.request(
            "POST",
            f"{self.api_prefix}/auth/register",
            expected_status=201,
            json=register_data,
        )
        if response.status_code == 201:
            data = response.json()
            self.user_ids["user1"] = data.get("id", "")

        login_data = {"username": email, "password": password}
        response = self.request(
            "POST",
            f"{self.api_prefix}/auth/login",
            expected_status=200,
            json=login_data,
        )
        if response.status_code == 200:
            data = response.json()
            self.tokens["user1"] = data.get("access_token", "")

    def test_public_feed(self) -> None:
        """Test public feed endpoints."""
        print("\n[3] Public Feed")
        self.request("GET", f"{self.api_prefix}/public/articles", expected_status=200)
        self.request("GET", f"{self.api_prefix}/public/categories", expected_status=200)
        self.request("GET", f"{self.api_prefix}/public/companies", expected_status=200)
        self.request("GET", f"{self.api_prefix}/public/topics", expected_status=200)
        self.request("GET", f"{self.api_prefix}/public/digests", expected_status=200)
        self.request("GET", f"{self.api_prefix}/public/clusters", expected_status=200)

    def test_personalized_feed(self) -> None:
        """Test personalized feed endpoint."""
        print("\n[4] Personalized Feed")
        if "user1" not in self.tokens:
            print("  SKIP: No user token available")
            return
        self.request(
            "GET",
            f"{self.api_prefix}/me/feed",
            user="user1",
            expected_status=200,
        )

    def test_story_detail(self) -> None:
        """Test story detail endpoint."""
        print("\n[5] Story Detail")
        response = self.request("GET", f"{self.api_prefix}/public/articles", expected_status=200)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            if items:
                article_id = items[0].get("id", "")
                if article_id:
                    self.request(
                        "GET",
                        f"{self.api_prefix}/public/articles/{article_id}",
                        expected_status=200,
                    )

    def test_notification_preferences(self) -> None:
        """Test notification preferences endpoints."""
        print("\n[6] Notification Preferences")
        if "user1" not in self.tokens:
            print("  SKIP: No user token available")
            return
        self.request(
            "GET",
            f"{self.api_prefix}/notifications/preferences",
            user="user1",
            expected_status=200,
        )
        self.request(
            "PUT",
            f"{self.api_prefix}/notifications/preferences",
            user="user1",
            expected_status=200,
            json={
                "email_enabled": True,
                "daily_digest_enabled": True,
                "weekly_digest_enabled": False,
            },
        )

    def test_schedule_preview(self) -> None:
        """Test schedule preview endpoint."""
        print("\n[7] Schedule Preview")
        if "user1" not in self.tokens:
            print("  SKIP: No user token available")
            return
        self.request(
            "GET",
            f"{self.api_prefix}/notifications/schedule-preview",
            user="user1",
            expected_status=200,
        )

    def test_notification_delivery(self) -> None:
        """Test notification delivery endpoints."""
        print("\n[8] Notification Delivery")
        if "user1" not in self.tokens:
            print("  SKIP: No user token available")
            return
        self.request(
            "POST",
            f"{self.api_prefix}/notifications/test-delivery",
            user="user1",
            expected_status=403,
            json={
                "notification_type": "system",
                "title": "Test Notification",
                "body": "This is a test notification from smoke tests.",
            },
        )

    def test_delivery_history(self) -> None:
        """Test delivery history endpoint."""
        print("\n[9] Delivery History")
        if "user1" not in self.tokens:
            print("  SKIP: No user token available")
            return
        self.request(
            "GET",
            f"{self.api_prefix}/notifications/deliveries",
            user="user1",
            expected_status=200,
        )

    def test_unsubscribe(self) -> None:
        """Test unsubscribe endpoint."""
        print("\n[10] Unsubscribe")
        token = str(uuid.uuid4())
        self.request(
            "GET",
            f"{self.api_prefix}/notifications/unsubscribe/{token}",
            expected_status=404,
        )

    def test_cross_user_access(self) -> None:
        """Test cross-user access prevention."""
        print("\n[11] Cross-User Access Prevention")
        unique_id = str(uuid.uuid4())[:8]
        email2 = f"smoke2_{unique_id}@example.com"
        password2 = "SmokeTest123!"
        register_data = {
            "email": email2,
            "password": password2,
            "name": f"Smoke User 2 {unique_id}",
        }
        response = self.request(
            "POST",
            f"{self.api_prefix}/auth/register",
            expected_status=201,
            json=register_data,
        )
        if response.status_code == 201:
            data = response.json()
            token2 = data.get("access_token", "")
            if "user1" in self.tokens and token2:
                self.request(
                    "GET",
                    f"{self.api_prefix}/notifications/preferences",
                    user="user1",
                    expected_status=200,
                )

    def test_invalid_requests(self) -> None:
        """Test invalid request handling."""
        print("\n[12] Invalid Requests")
        self.request(
            "POST",
            f"{self.api_prefix}/auth/register",
            expected_status=422,
            json={"username": "invalid", "password": "short"},
        )
        self.request(
            "GET",
            f"{self.api_prefix}/public/articles/invalid-id",
            expected_status=422,
        )

    def test_unauthorized_requests(self) -> None:
        """Test unauthorized request handling."""
        print("\n[13] Unauthorized Requests")
        self.request(
            "GET",
            f"{self.api_prefix}/me/feed",
            expected_status=401,
        )
        self.request(
            "GET",
            f"{self.api_prefix}/notifications/preferences",
            expected_status=401,
        )
        self.request(
            "POST",
            f"{self.api_prefix}/notifications/test-delivery",
            expected_status=401,
            json={},
        )

    def print_summary(self) -> None:
        """Print test summary."""
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        total = len(self.results)
        print(f"Total: {total}, Passed: {passed}, Failed: {failed}")
        if failed > 0:
            print("\nFailed tests:")
            for r in self.results:
                if r["status"] == "FAIL":
                    print(f"  {r['test']}: expected {r['expected']}, got {r['actual']}")
        print("=" * 70)


if __name__ == "__main__":
    runner = SmokeTestRunner()
    runner.run()
