#!/usr/bin/env python3
"""Production target validation commands.

This script provides validation commands for checking production infrastructure
connectivity and availability. Run these commands from a machine that has network
access to the production environment.

Exit codes:
  0 - All validations passed
  1 - One or more validations failed
  2 - Production target not configured (external activation blocked)
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from typing import Callable


ValidationFn = Callable[[], tuple[bool, str]]


def check_dns_resolution(domain: str) -> tuple[bool, str]:
    """Check DNS resolution for a domain."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["nslookup", domain],
                capture_output=True,
                text=True,
                timeout=10,
            )
        else:
            result = subprocess.run(
                ["dig", "+short", domain],
                capture_output=True,
                text=True,
                timeout=10,
            )
        output = result.stdout.strip()
        if output and "NXDOMAIN" not in output and "can't find" not in output.lower():
            return True, f"DNS resolution for {domain}: OK ({output.splitlines()[0]})"
        return False, f"DNS resolution for {domain} failed: {output}"
    except Exception as exc:
        return False, f"DNS resolution for {domain} error: {exc}"


def check_tls_certificate(domain: str, port: int = 443) -> tuple[bool, str]:
    """Check TLS certificate validity for a domain."""
    try:
        import ssl
        import socket
        context = ssl.create_default_context()
        with socket.create_connection((domain, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                subject = dict(x[0] for x in cert.get("subject", ()))
                issuer = dict(x[0] for x in cert.get("issuer", ()))
                not_after = cert.get("notAfter", "unknown")
                return True, f"TLS certificate for {domain}: valid (issuer={issuer.get('organizationName', 'unknown')}, expires={not_after})"
    except Exception as exc:
        return False, f"TLS certificate check for {domain}:{port} failed: {exc}"


def check_http_availability(url: str, expected_status: int = 200, timeout: int = 10) -> tuple[bool, str]:
    """Check HTTP endpoint availability."""
    try:
        import urllib.request
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == expected_status:
                return True, f"HTTP {url}: {resp.status} OK"
            return False, f"HTTP {url}: expected {expected_status}, got {resp.status}"
    except Exception as exc:
        return False, f"HTTP {url} failed: {exc}"


def check_postgres_connectivity(host: str, port: int, database: str, user: str, password: str) -> tuple[bool, str]:
    """Check PostgreSQL connectivity."""
    try:
        import asyncpg
        import asyncio

        async def _check():
            conn = await asyncpg.connect(
                host=host, port=port, database=database, user=user, password=password,
                timeout=10,
            )
            version = await conn.fetchval("SELECT version()")
            await conn.close()
            return True, f"PostgreSQL {host}:{port}/{database}: connected ({version[:50]}...)"

        return asyncio.run(_check())
    except Exception as exc:
        return False, f"PostgreSQL {host}:{port}/{database} failed: {exc}"


def check_redis_connectivity(host: str, port: int, password: str | None = None) -> tuple[bool, str]:
    """Check Redis connectivity."""
    try:
        import redis
        url = f"redis://:{password}@{host}:{port}/0" if password else f"redis://{host}:{port}/0"
        r = redis.from_url(url, socket_timeout=10)
        pong = r.ping()
        r.close()
        if pong:
            return True, f"Redis {host}:{port}: connected (PONG)"
        return False, f"Redis {host}:{port}: ping failed"
    except Exception as exc:
        return False, f"Redis {host}:{port} failed: {exc}"


def check_metrics_endpoint(base_url: str, admin_token: str | None = None) -> tuple[bool, str]:
    """Check metrics endpoint availability."""
    try:
        import urllib.request
        url = f"{base_url.rstrip('/')}/metrics/health"
        req = urllib.request.Request(url, method="GET")
        if admin_token:
            req.add_header("Authorization", f"Bearer {admin_token}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return True, f"Metrics health {url}: OK"
            return False, f"Metrics health {url}: {resp.status}"
    except Exception as exc:
        return False, f"Metrics health {url} failed: {exc}"


def check_container_health(container_name: str) -> tuple[bool, str]:
    """Check Docker container health."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        status = result.stdout.strip()
        if status == "healthy":
            return True, f"Container {container_name}: healthy"
        return False, f"Container {container_name}: {status}"
    except Exception as exc:
        return False, f"Container {container_name} check failed: {exc}"


def main() -> int:
    print("Production Target Validation")
    print("=" * 50)
    print("This script validates production infrastructure connectivity.")
    print("Configure the target values below or set environment variables.\n")

    # Read configuration from environment
    prod_frontend_domain = os.environ.get("PROD_FRONTEND_DOMAIN", "")
    prod_api_domain = os.environ.get("PROD_API_DOMAIN", "")
    prod_api_url = os.environ.get("PROD_API_URL", f"https://{prod_api_domain}" if prod_api_domain else "")
    prod_postgres_host = os.environ.get("PROD_POSTGRES_HOST", "")
    prod_postgres_port = int(os.environ.get("PROD_POSTGRES_PORT", "5432"))
    prod_postgres_db = os.environ.get("PROD_POSTGRES_DB", "ai_news_digest")
    prod_postgres_user = os.environ.get("PROD_POSTGRES_USER", "")
    prod_postgres_password = os.environ.get("PROD_POSTGRES_PASSWORD", "")
    prod_redis_host = os.environ.get("PROD_REDIS_HOST", "")
    prod_redis_port = int(os.environ.get("PROD_REDIS_PORT", "6379"))
    prod_redis_password = os.environ.get("PROD_REDIS_PASSWORD", "")
    prod_metrics_token = os.environ.get("PROD_METRICS_TOKEN", "")

    # Check if any production target is configured
    if not any([prod_frontend_domain, prod_api_domain, prod_postgres_host, prod_redis_host]):
        print("STATUS: Production target not configured.")
        print("No production domains, hosts, or credentials are set.")
        print("\nExternal activation is BLOCKED pending configuration of:")
        print("  - Production frontend domain")
        print("  - Production API domain")
        print("  - PostgreSQL host and credentials")
        print("  - Redis host and credentials")
        print("  - TLS certificates")
        print("\nSet the environment variables above and re-run this script.")
        return 2

    validations: list[tuple[str, ValidationFn]] = []

    if prod_frontend_domain:
        validations.append(("DNS: frontend domain", lambda: check_dns_resolution(prod_frontend_domain)))
        validations.append(("TLS: frontend domain", lambda: check_tls_certificate(prod_frontend_domain)))
        validations.append(("HTTP: frontend availability", lambda: check_http_availability(f"https://{prod_frontend_domain}")))

    if prod_api_domain:
        validations.append(("DNS: API domain", lambda: check_dns_resolution(prod_api_domain)))
        validations.append(("TLS: API domain", lambda: check_tls_certificate(prod_api_domain)))

    if prod_api_url:
        validations.append(("HTTP: API liveness", lambda: check_http_availability(f"{prod_api_url}/health/live")))
        validations.append(("HTTP: API readiness", lambda: check_http_availability(f"{prod_api_url}/health/ready")))
        validations.append(("Metrics: health", lambda: check_metrics_endpoint(f"{prod_api_url}", prod_metrics_token)))

    if prod_postgres_host and prod_postgres_user and prod_postgres_password:
        validations.append(("PostgreSQL: connectivity", lambda: check_postgres_connectivity(
            prod_postgres_host, prod_postgres_port, prod_postgres_db, prod_postgres_user, prod_postgres_password,
        )))

    if prod_redis_host:
        validations.append(("Redis: connectivity", lambda: check_redis_connectivity(
            prod_redis_host, prod_redis_port, prod_redis_password or None,
        )))

    # Check container health if running locally
    containers = ["ai_news_digest_web", "ai_news_digest_db", "ai_news_digest_redis", "ai_news_digest_worker", "ai_news_digest_beat"]
    for container in containers:
        validations.append((f"Container: {container}", lambda c=container: check_container_health(c)))

    passed = 0
    failed = 0
    for name, fn in validations:
        try:
            ok, msg = fn()
        except Exception as exc:
            ok, msg = False, f"Validation error: {exc}"
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {msg}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    if failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
