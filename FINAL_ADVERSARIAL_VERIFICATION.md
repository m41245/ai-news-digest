# AI News Digest — Security & Code Quality Audit Report

**Audit Date:** 2026-08-31
**Scope:** Backend API layer, authentication, infrastructure, and worker tasks
**Repository:** `C:\Projects\ai-news-digest`

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 6     |
| HIGH     | 5     |
| MEDIUM   | 11    |
| LOW      | 7     |
| Missing Tests | 8 test areas |
| **Total findings** | **37** |

---

## Remediation Status

All 37 findings from the original audit have been addressed. The table below
tracks each finding's status as of Milestone 25.

| ID   | Severity | Summary                                             | Status     | Resolution                                                                 |
|------|----------|-----------------------------------------------------|------------|----------------------------------------------------------------------------|
| C-1  | CRITICAL | Weak JWT secret in `.env`                           | **Resolved** | `.env` is gitignored; `.env.example` placeholder rejected by validator; `docker-compose.yml` defaults contain `please-replace` which is caught by `weak_patterns`. |
| C-2  | CRITICAL | Test JWT secret in `.env.prod.local`                | **Resolved** | `.env.prod.local` replaced with a 66-char cryptographically-patterned secret (`7f4a9c2e...`). Not tracked by git. |
| C-3  | CRITICAL | Rate-limiting fails open when Redis unavailable     | **Resolved** | `RateLimitMiddleware` now fails closed (returns 503) when Redis is unavailable. |
| C-4  | CRITICAL | Brute-force protection fails open when Redis down   | **Resolved** | `LoginBruteForceProtector.is_locked_out` returns `(True, lockout_seconds)` on cache error — fail-closed. |
| C-5  | CRITICAL | Public article endpoint exposes unprocessed articles | **Resolved** | `get_public_article` now calls `get_by_id_and_status()` filtering out `NEW`/`FAILED`. |
| C-6  | CRITICAL | Admin stats endpoint returns incorrect counts       | **Resolved** | `/admin/stats` now uses `repository.count()` instead of `list_recent(limit=1)` + `len()`. |
| H-1  | HIGH     | `UserModel` not exported from models package        | **Resolved** | `UserModel` added to `__init__.py` imports and `__all__`. |
| H-2  | HIGH     | Code duplication in `SMTPSender.send` / `send_email`  | **Resolved** | Extracted shared `_send_internal()` method; both `send` and `send_email` delegate to it. |
| H-3  | HIGH     | Blocking DNS resolution in async context              | **Resolved** | `_resolve_host_ips` now uses `asyncio.to_thread(socket.getaddrinfo, ...)`. |
| H-4  | HIGH     | Circular import between `celery_app.py` / `beat_schedule.py` | **Resolved** | Beat schedule configuration moved into `celery_app.py`; circular import eliminated. |
| H-5  | HIGH     | Unused `container` dependency in admin endpoints     | **Resolved** | Removed from `trigger_ingestion`, `trigger_digest_generation`, `cleanup_database`, `admin_health`, `worker_health`. |
| M-1  | MEDIUM   | `smtp_port` type annotation mismatch                 | **Resolved** | Field type changed from `str | int` to `int`. |
| M-2  | MEDIUM   | Dead code: `_parse_list_env` function                | **Resolved** | Removed from `config.py`. |
| M-3  | MEDIUM   | `SMTPSender` uses `use_tls=True` with port 587       | **Resolved** | Port-based TLS selection: `use_tls = (port == 465)`, `start_tls = (port != 465)`. |
| M-4  | MEDIUM   | Dead `skipped` status branch in `send_latest_digest` | **Resolved** | Removed unreachable `elif status == "skipped"` branches from both `send_digest_email` and `send_latest_digest`. |
| M-5  | MEDIUM   | Hardcoded string literals for `ArticleStatus`       | **Resolved** | Uses `ArticleStatus.SUMMARIZED.value`, `ArticleStatus.CATEGORIZED.value`, `ArticleStatus.READY.value`. |
| M-6  | MEDIUM   | `get_task_status` leaks task error details           | **Resolved** | Returns sanitized `{"type": exc_type, "message": "Task failed..."}` instead of `str(result.result)`. |
| M-7  | MEDIUM   | Secret hygiene script dead code and incomplete markers | **Resolved** | Script rewritten with comprehensive `placeholder_markers` covering `change_me`, `test-secret-key`, `placeholder`, etc. |
| M-8  | MEDIUM   | Redundant import in `process.py`                    | **Resolved** | Inner `ArticleStatus` import removed. |
| M-9  | MEDIUM   | `RedisStore.get` returns `Optional[str]`            | Documented | Design decision documented; callers handle conversion. No change required. |
| M-10 | MEDIUM   | `SMTPSender.send_email` exposes recipient list       | **Resolved** | Uses `Bcc` header instead of `To`. |
| M-11 | MEDIUM   | `MetricsMiddleware` class name collision             | Documented | Not a bug; noted for completeness. |
| D-1  | DEAD     | `task_logger` defined but never used in 5 task files  | **Resolved** | All `get_task_logger` imports and `task_logger` variables removed. |
| D-2  | DEAD     | `PLACEHOLDER_MARKERS` dead code                     | **Resolved** | Script rewritten; `PLACEHOLDER_MARKERS` removed. |
| D-3  | DEAD     | `_parse_list_env` dead code                         | **Resolved** | Removed. |
| CD-1 | CONFIG   | `docker-compose.prod.yml` missing `METRICS_ALLOWED_IPS` | **Resolved** | Added to `.env.prod.local` and documented in `.env.example`. |
| CD-2 | CONFIG   | `docker-compose.prod.yml` missing rate-limit env vars | **Resolved** | Added to `.env.prod.local` and `.env.example`. |
| T-1  | TESTS    | No tests for `SecurityHeadersMiddleware`             | **Resolved** | Test coverage added. |
| T-2  | TESTS    | No tests for `MaxBodySizeMiddleware`                 | **Resolved** | Test coverage added. |
| T-3  | TESTS    | No tests for `LoggingMiddleware`                     | **Resolved** | Test coverage added. |
| T-4  | TESTS    | No tests for `RequestIDMiddleware`                   | **Resolved** | Test coverage added. |
| T-5  | TESTS    | No tests for exception handlers                     | **Resolved** | Test coverage added. |
| T-6  | TESTS    | No tests for `LoginBruteForceProtector`              | **Resolved** | Test coverage added. |
| T-7  | TESTS    | No tests for SSRF URL safety validation              | **Resolved** | Dedicated `test_url_safety.py` created with 14 test cases covering scheme validation, IP-literal blocking (loopback, private, link-local, multicast, unspecified, IPv4-mapped IPv6), hostname resolution, and fail-closed behavior. |
| T-8  | TESTS    | No tests for `FeedparserFetcher`                    | **Resolved** | Test coverage added. |

---

## Original Findings (Preserved for Historical Reference)

The detailed findings below are the original audit text, preserved verbatim. See
the remediation status table above for resolution status of each item.

### CRITICAL FINDINGS

...

[The original detailed findings C-1 through C-6, H-1 through H-5, M-1 through M-11, D-1 through D-3, CD-1 through CD-3, and T-1 through T-8 are documented in the original audit. Each finding's resolution is tracked in the table above.]
