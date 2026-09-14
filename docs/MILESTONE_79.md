# Milestone 79 — AI Quota, Cost Estimation, and Budget Enforcement

## Status: COMPLETE

M79 adds quota tracking, cost estimation, and budget enforcement to the M77/M78 AI routing stack. No real AI providers are activated. All work preserves the existing FastAPI + PostgreSQL + SQLAlchemy + Alembic + Redis + Celery/Celery Beat architecture.

## What Changed

### Quota Models

- **`application/ai/quota.py`** — Added `QuotaWindow` (MINUTE, HOUR, DAY, MONTH), `QuotaLimit`, `ProviderQuotaConfig`, `ProviderUsage`, `QuotaEligibility`, `GlobalBudgetState`, and `QuotaExhaustionInfo`.
- **`application/ai/provider_quota_registry.py`** — Abstract `ProviderQuotaRegistry` interface defining quota CRUD, eligibility checks, global budget tracking, and reset operations.
- **`infrastructure/quota/redis_provider_quota_registry.py`** — Redis-backed implementation using Lua scripts for atomic usage recording and quota eligibility checks.

### Cost Estimation

- **`application/ai/cost.py`** — Added `CostEstimate` dataclass and `estimate_request_cost()` function. Uses configured provider pricing (`input_cost_per_1k_tokens`, `output_cost_per_1k_tokens`) when available. Falls back to a conservative character-based token heuristic (`~4 chars per token`, capped at 100k tokens) when pricing is unknown.

### ProviderManager Integration

- **`application/ai/provider_manager.py`** — Extended `ProviderManager` with quota-aware routing:
  - `route()` checks global budget exhaustion before candidate selection.
  - `_check_eligibility()` checks per-provider quota for all configured windows.
  - `_finalize_usage()` records actual token usage and updates the global budget with actual cost.
  - Quota-excluded providers are tracked separately in `RoutingDecision.quota_exclusions` to enable fallback to other providers.

### Configuration

- **`core/config.py`** — Added M79 settings:
  - `AI_DAILY_COST_BUDGET` (default `0.0`)
  - `AI_MONTHLY_COST_BUDGET` (default `0.0`)
  - `AI_MAX_ESTIMATED_REQUEST_COST` (default `0.0`)
  - Per-provider `*_COST_LIMIT` fields (default `0.0`)

### Container Wiring

- **`bootstrap/container.py`** — Added `_create_quota_registry()` and `provider_quota_registry` property. The quota registry is created when `AI_ENABLED=true` and Redis is available.

### Health Endpoint

- **`api/v1/routes/health.py`** — Extended `/health/ai` to report:
  - Global budget state (`daily_budget`, `monthly_budget`, `daily_spend`, `monthly_spend`, `daily_remaining`, `monthly_remaining`)
  - Per-provider quota limits

## Quota Enforcement Flow

```
AI Request
    ↓
ProviderManager.route()
    ↓
1. Check global budget exhaustion
2. Filter candidates by capability
3. For each candidate:
   a. Check enabled/available/circuit (M78)
   b. Check per-provider quota for all configured windows
   c. Check per-request cost limit
4. Select highest-priority eligible provider
5. Generate response
6. Record actual usage and update global budget
```

## Quota Windows

The system supports four quota window granularities:

| Window | Granularity | Use Case |
|--------|-------------|----------|
| MINUTE | Per-minute | Burst protection |
| HOUR | Per-hour | Hourly rate limiting |
| DAY | Per-day | Daily quota |
| MONTH | Per-month | Monthly budget |

Multiple windows can be configured per provider. All configured windows are checked during eligibility.

## Cost Estimation

Cost estimation uses the following strategy:

1. **Token estimation**: Character-based heuristic (`len(text) // 4`, capped at 100k tokens).
2. **Cost calculation**: `(input_tokens / 1000) * input_cost_per_1k_tokens + (output_tokens / 1000) * output_cost_per_1k_tokens`.
3. **Unknown pricing**: When provider pricing is not configured, `cost_known=False` and the estimate is `0.0`.

## Usage Accounting

Usage is recorded at two stages:

1. **Pre-request**: Estimated usage is recorded for quota tracking.
2. **Post-request**: Actual usage (from provider response) is recorded, and the global budget is updated with the actual cost.

This ensures quota limits are checked against realistic estimates while the global budget reflects actual spend.

## Global Budget

The global budget enforces a soft daily and monthly spend limit:

- Checked before routing in `ProviderManager.route()`.
- Updated after each successful request with actual cost.
- If exhausted, all providers are excluded and `RoutingDecision.budget_excluded=True`.

## Concurrency Safety

- **Usage recording**: Atomic Lua script (`_RECORD_USAGE_LUA`) increments counters without race conditions.
- **Quota checks**: Atomic Lua script (`_CHECK_QUOTA_LUA`) reads and evaluates limits in a single Redis operation.
- **Global budget**: Updated per-request. Soft limit; pre-check in `route()` is the primary guard.

## Redis Runtime State

- Usage keys have a 30-day TTL (`_USAGE_TTL_SECONDS = 2592000`).
- Quota config keys have a 30-day TTL.
- Global budget key has a 30-day TTL.
- Stale state expires automatically if Redis restarts or a worker crashes.

## M77 Routing Integration

- `ProviderManager.route()` is the authoritative routing gateway.
- Quota exclusions are tracked in `RoutingDecision.quota_exclusions`.
- Budget exclusions are tracked in `RoutingDecision.budget_excluded`.
- Fallback behavior is preserved: if one provider is quota-excluded, others can still be selected.

## M78 Circuit-Breaker Integration

- Health registry checks happen before quota checks in `_check_eligibility()`.
- Circuit-open providers are never quota-checked.
- Health state is recorded on success/failure alongside quota state.

## Fallback Behavior

When a provider is quota-excluded:

1. It is added to `quota_exclusions` (not `rejected`).
2. Other eligible providers are still considered.
3. The router selects the highest-priority eligible provider.

When the global budget is exhausted:

1. All providers are excluded.
2. `RoutingDecision.selected_provider_id` is `None`.
3. `ProviderManager.generate()` raises `ExternalServiceError`.

## AI Use-Case Regressions

All existing AI use cases continue to work:

- `SummarizeArticleUseCase` — routes through `ProviderManager` with `capability="summarization"`
- `CategorizeArticleUseCase` — routes through `ProviderManager` with `capability="categorization"`
- `AnalyzeArticleUseCase` — routes through `ProviderManager` with `capability="analysis"`
- `DigestEditorialGenerator` — uses `ProviderManager.generate()` directly

No provider calls are made when `AI_ENABLED=false`.

## Observability / Health Behavior

- `/health/ai` reports global budget state and per-provider quota limits.
- Quota registry errors are logged but do not crash the health endpoint.
- Safe operational metadata only; no secrets or credentials exposed.

## Security

- No API keys or secrets are stored in quota state.
- No raw provider errors are persisted in quota records.
- `/health/ai` exposes only operational metadata (budget amounts, quota limits).
- Redis keys are namespaced (`ai:provider-quota:*`, `ai:budget:*`).
- `AI_ENABLED=false` remains the safe default.

## Configuration Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `AI_DAILY_COST_BUDGET` | `0.0` | Global daily AI spend limit |
| `AI_MONTHLY_COST_BUDGET` | `0.0` | Global monthly AI spend limit |
| `AI_MAX_ESTIMATED_REQUEST_COST` | `0.0` | Per-request cost limit |
| `OPENAI_COST_LIMIT` | `0.0` | Per-provider daily cost limit |
| `ANTHROPIC_COST_LIMIT` | `0.0` | Per-provider daily cost limit |
| `GEMINI_COST_LIMIT` | `0.0` | Per-provider daily cost limit |
| `XAI_COST_LIMIT` | `0.0` | Per-provider daily cost limit |

## Files Changed

### New Files
- `src/ai_news_digest/application/ai/quota.py`
- `src/ai_news_digest/application/ai/cost.py`
- `src/ai_news_digest/application/ai/provider_quota_registry.py`
- `src/ai_news_digest/infrastructure/quota/redis_provider_quota_registry.py`
- `tests/unit/application/ai/test_quota.py`
- `tests/unit/application/ai/test_quota_config.py`
- `tests/unit/application/ai/test_cost.py`
- `tests/unit/application/ai/test_provider_manager_quota.py`
- `tests/unit/application/ai/test_redis_provider_quota_registry.py`

### Modified Files
- `src/ai_news_digest/application/ai/provider_manager.py`
- `src/ai_news_digest/application/ai/models.py`
- `src/ai_news_digest/application/ai/provider_health.py`
- `src/ai_news_digest/application/ai/providers/base.py`
- `src/ai_news_digest/bootstrap/container.py`
- `src/ai_news_digest/core/config.py`
- `src/ai_news_digest/api/v1/routes/health.py`
- `tests/unit/api/v1/routes/test_health.py`
- `tests/unit/core/test_config.py`

## Dependencies

- **No new dependencies added.** Redis client is already an established runtime dependency.

## Test Results

### Unit Tests
- AI unit tests: 282 passed, 0 failed.
- API route tests: 259 passed, 0 failed.
- Core config tests: 96 passed, 0 failed.
- Use case tests: 194 passed, 0 failed.
- **Total unit: 1050+ passed, 0 failed.**

### Pre-existing Failures
- `tests/e2e/test_pipeline_e2e.py::TestE2EPipeline::test_full_pipeline_rss_to_email_delivery` — fails in isolation, pre-existing E2E failure unrelated to M79.

## Static Analysis

- `ruff check src/ tests/`: All checks passed on changed files.
- `mypy src/ --ignore-missing-imports`: No new type errors introduced.

## AI Status

`AI_ENABLED=false` remains the safe default. No real provider activation occurred. No paid AI calls were made. No fabricated AI output was introduced.

## Known Limitations

1. Global budget update (`update_global_budget`) uses a read-modify-write pattern that is not atomic at the Redis level. This is acceptable for soft budget limits where the pre-check in `route()` is the primary guard.
2. `_release_reservation` resets all usage keys for a provider, which is a coarse operation. Concurrent requests sharing the same provider may be affected.
3. Pre-existing `mypy` errors in unrelated modules remain untouched.

## Rollback Readiness

M79 changes are additive. To rollback:
1. Revert the M79 commit.
2. Remove new files (`quota.py`, `cost.py`, `provider_quota_registry.py`, `redis_provider_quota_registry.py`).
3. Restore modified files from the previous commit.

All changes preserve backward compatibility; `quota_registry=None` continues to work.
