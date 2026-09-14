# M78 — Provider Health and Circuit Breakers

## Architecture

M78 extends the M77 dynamic router with a provider health and circuit-breaker subsystem.

```
AI Use Case
    ↓
ProviderManager / AI Gateway
    ↓
RoutingContext
    ↓
DecisionEngine / Routing Policy
    ↓
Provider Health Registry (M78)
    ↓
Circuit Breaker
    ↓
Provider Registry
    ↓
Provider Adapter
    ↓
OpenAI / Anthropic / Gemini / Grok
```

Provider health state is shared across FastAPI processes and Celery workers via Redis.

## State Machine

```
CLOSED
  │
  │ threshold qualifying failures
  ▼
OPEN
  │
  │ cooldown expires
  ▼
HALF_OPEN
  │             │
 success        failure
  │             │
  ▼             ▼
CLOSED         OPEN
```

### States

| State | Meaning |
|-------|---------|
| `CLOSED` | Provider is healthy and eligible for normal routing. |
| `OPEN` | Provider has exceeded the failure threshold. It is excluded from routing until cooldown expires. |
| `HALF_OPEN` | Cooldown has expired. One bounded probe request is permitted to test recovery. |

## Health Model

Each provider has a `ProviderHealthState` containing:

- `provider_id`
- `state` (CLOSED / OPEN / HALF_OPEN)
- `consecutive_failures`
- `consecutive_successes`
- `last_failure_at`
- `last_success_at`
- `opened_at`
- `cooldown_until`
- `next_probe_at`

## Failure Classification

Failures are classified using the existing `application.ai.errors` hierarchy:

| Failure Category | Counts Toward Circuit? | Fallback? | Notes |
|------------------|------------------------|-----------|-------|
| `TIMEOUT` | Yes | Yes | Transient network/provider delay |
| `TEMPORARY_FAILURE` | Yes | Yes | 5xx, connection resets |
| `PROVIDER_UNAVAILABLE` | Yes | Yes | Provider unreachable |
| `RATE_LIMITED` | Yes | Yes | HTTP 429; may open circuit |
| `AUTHENTICATION_FAILURE` | Yes | Yes | Invalid/expired API key |
| `INVALID_RESPONSE` | Yes | Yes | Malformed provider response |
| `CONFIGURATION_ERROR` | No | Yes | Missing config; setup issue |
| `UNSUPPORTED_CAPABILITY` | No | No | Provider cannot handle request |
| `PERMANENT_PROCESSING_ERROR` | No | No | Definite failure; no retry |
| `INVALID_REQUEST` | No | No | Bad application input |

### Authentication Failure Policy

A provider returning an authentication failure will have its circuit opened after the configured threshold. This prevents retry storms against providers with invalid credentials. The circuit can be manually reset when the credential is corrected.

## Failure Threshold

Configuration:

- `AI_PROVIDER_FAILURE_THRESHOLD` (default: `3`)
- `AI_PROVIDER_CIRCUIT_COOLDOWN_SECONDS` (default: `60`)
- `AI_PROVIDER_SUCCESS_THRESHOLD_TO_CLOSE` (default: `1`)

Three consecutive qualifying failures open the circuit.

## Cooldown

When a circuit opens:

- `opened_at` is recorded
- `cooldown_until = opened_at + cooldown_seconds`
- The provider is excluded from routing until cooldown expires

## Half-Open Probing

After cooldown expires:

1. The next request attempts to acquire a probe lease via Redis `SET NX EX`
2. Only one concurrent probe per provider is permitted
3. If the probe succeeds → `CLOSED`
4. If the probe fails → `OPEN` with a fresh cooldown

## Concurrency Safety

All state transitions are protected:

- In-memory registry uses `threading.Lock`
- Redis registry uses Lua scripts for atomic read-modify-write
- Probe lease uses Redis `SET NX EX` for atomic acquisition

## State Store

**Redis** is used because:

- It is already an established runtime dependency
- FastAPI and Celery workers run in separate processes
- Health state must be consistent across processes
- Redis supports atomic Lua scripts and TTL-based key expiration

### Redis Key Namespace

```
ai:provider-health:{provider_id}          # Health state hash
ai:provider-health:probe-lease:{provider_id}  # Probe lease (TTL = 5s)
```

### TTL and Stale State

- Keys are given a TTL that exceeds the cooldown period
- If a worker crashes or Redis restarts, stale OPEN states expire automatically
- Every OPEN circuit has a guaranteed recovery path via TTL

### Redis Failure Behavior

If Redis is unavailable:

- The health registry raises an exception
- `ProviderManager` catches the exception and logs a warning
- Routing continues without health-aware filtering (M77 behavior)
- The AI system does not crash

## Health-Aware Routing

The routing decision flow is:

1. `AI_ENABLED` check
2. Capability filtering
3. Enabled/configured filtering
4. **Health/circuit eligibility (M78)**
5. Excluded providers
6. Preferred provider
7. Priority ordering
8. Deterministic selection

An `OPEN` provider is never selected. A `HALF_OPEN` provider is only selected for an authorized recovery probe.

### Preferred Provider + Circuit Breaker

Health always overrides preference. If the preferred provider is `OPEN`, the router selects the next eligible provider.

## Health Endpoint

`GET /health/ai` reports:

- `circuit_state` (closed / open / half_open / unknown)
- `available_for_routing`
- `consecutive_failures`
- `last_success`
- `last_failure`
- `cooldown_until`

The endpoint does **not** call external AI providers. It reports local Redis-backed health state.

## Metrics

Existing in-process metrics are extended:

- `ai_provider_failures_total` — incremented on every provider failure
- `ai_provider_requests_total` — incremented on every provider request
- `ai_processing_latencies` — latency samples per provider

Structured logging events:

- `provider_circuit_opened`
- `provider_circuit_half_open`
- `provider_circuit_closed`
- `provider_circuit_reopened`
- `provider_health_failure`
- `provider_health_success`

## Testing

### Unit Tests

- `tests/unit/application/ai/test_provider_health.py` — health model, failure classification
- `tests/unit/application/ai/test_circuit_breaker.py` — in-memory circuit breaker state machine
- `tests/unit/application/ai/test_provider_manager_health.py` — routing integration

### Integration Tests

- `tests/integration/application/ai/test_circuit_breaker_redis.py` — Redis-backed state transitions, TTL, probe lease

### Test Coverage

All M78 tests use mocks/fakes. No real AI provider calls are required.

## Security

- No API keys or secrets are stored in health state
- No raw provider errors are persisted
- Health endpoint exposes only safe operational metadata
- No public endpoint allows arbitrary provider control
- Redis keys are namespaced and not exposed publicly

## What M78 Does NOT Implement

- Quota tracking (M79)
- Cost-aware routing (M79)
- Quality benchmarking (M80)
- Evidence intelligence (M81+)
- Breaking-story detection (M81+)
- Personalization (M81+)

## Configuration Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `AI_PROVIDER_FAILURE_THRESHOLD` | `3` | Consecutive qualifying failures to open circuit |
| `AI_PROVIDER_CIRCUIT_COOLDOWN_SECONDS` | `60` | Seconds before an open circuit can be probed |
| `AI_PROVIDER_HALF_OPEN_PROBE_TIMEOUT_SECONDS` | `30` | Timeout for half-open probe requests |
| `AI_PROVIDER_SUCCESS_THRESHOLD_TO_CLOSE` | `1` | Consecutive successes to close a half-open circuit |

## Operational Reset

To reset a provider circuit programmatically:

```python
from ai_news_digest.application.ai.provider_health_registry import ProviderHealthRegistry

registry: ProviderHealthRegistry = container.provider_health_registry
await registry.reset("openai")
```

This transitions `OPEN → CLOSED` only when explicitly requested.
