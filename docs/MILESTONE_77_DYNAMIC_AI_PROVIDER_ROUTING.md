# Milestone 77 — Dynamic AI Provider Routing

## Status: COMPLETE

## Architecture

```
AI Use Case
     ↓
AI Gateway (ProviderManager)
     ↓
Routing Decision
     ↓
Provider Registry
     ↓
Eligible Providers
     ↓
Routing Policy
     ↓
Selected Provider
     ↓
Provider Adapter
     ↓
External AI API
```

## What Changed

M77 transforms the static provider priority model from M76 into a dynamic, capability-aware routing system. The key changes are:

1. **Routing Decision Model** — Added `RoutingContext` and `RoutingDecision` dataclasses to `application/ai/models.py` for structured, explainable routing outcomes.

2. **Dynamic ProviderManager** — Refactored `ProviderManager` from a simple priority iterator into a full routing gateway with:
   - Capability-aware candidate filtering via `DecisionEngine`
   - Provider eligibility checks (enabled, available, capable)
   - Optional preferred provider selection
   - Optional excluded providers
   - Deterministic priority-based selection with provider_id tie-breaking
   - Bounded sequential fallback on failure
   - Structured routing decision metadata

3. **Application Integration** — Updated AI use cases to route through `ProviderManager` with capability hints:
   - `SummarizeArticleUseCase` → `capability="summarization"`
   - `CategorizeArticleUseCase` → `capability="categorization"`
   - `AnalyzeArticleUseCase` → `capability="analysis"`
   - `DigestEditorialGenerator` → uses `ProviderManager.generate()` directly

4. **Container Wiring** — Updated `Container` to construct `ProviderManager` with its full dependency set (registry, capability registry, decision engine).

## Routing Policy

The router applies the following decision order:

1. **AI_ENABLED check** — If `AI_ENABLED=false`, return "AI is disabled" immediately.
2. **Capability filtering** — Only providers advertising the requested capability become candidates.
3. **Excluded provider filtering** — Request-level exclusions are applied.
4. **Eligibility filtering** — Each candidate is checked for:
   - `enabled` flag
   - `available()` returns True (credentials configured, client initialized)
   - capability support (redundant with step 2, but explicit)
5. **Preferred provider** — If specified and eligible, it is ranked first.
6. **Priority ordering** — Remaining candidates sorted by configured priority descending.
7. **Deterministic tie-break** — Provider ID ascending for stable ordering.
8. **Selection** — First candidate in sorted order is selected.

## Provider Eligibility

A provider must satisfy all of the following to be eligible:

- `provider.enabled is True`
- `await provider.available() is True`
- `capability in provider.capabilities` (when capability is specified)

Unavailable providers are never selected. Providers without credentials are never selected. Disabled providers are never selected.

## Capability-Aware Routing

Routing always considers capability before priority. For example:

```
Request: ARTICLE_ANALYSIS (capability="analysis")
```

Only providers advertising the `analysis` capability become candidates. Providers that only support `summarization` or `categorization` are never considered for this request.

## Request Context

The routing system accepts an extensible request context:

- `capability` — Required capability for the request
- `preferred_provider` — Optional explicit provider preference
- `excluded_providers` — Optional request-level exclusions

Future extension points (not implemented in M77):
- `quality_requirement`
- `latency_requirement`
- `cost_requirement`

## Explicit Provider Preference

When `preferred_provider` is specified and the provider is:
- configured
- enabled
- available
- capable

It is selected first. If the preferred provider is unavailable or incapable, the router safely falls back to other eligible providers. An invalid provider ID does not bypass capability checks.

## Excluded Providers

Request-level exclusions prevent specific providers from being selected. This is useful for:
- Retries
- Fallback scenarios
- Testing

Excluded providers are never selected, even if they would otherwise be the highest-priority candidate.

## Dynamic Priority

The router uses configured provider priority as the primary ranking signal. Priority is applied after eligibility and preference filtering. The exact priority values are configured via environment variables:

```env
OPENAI_PRIORITY=1
ANTHROPIC_PRIORITY=2
GEMINI_PRIORITY=3
XAI_PRIORITY=4
```

## Deterministic Routing

Routing is fully deterministic. Given the same:
- request
- configuration
- provider availability
- provider metadata

The router makes the same decision. Selection uses:
1. Priority descending
2. Provider ID ascending (tie-break)

No random selection, no timestamp-dependent ordering, no unstable iteration.

## Routing Decision Object

Every routing decision produces a structured `RoutingDecision`:

```python
@dataclass(slots=True)
class RoutingDecision:
    selected_provider_id: str | None
    capability: str | None
    candidate_provider_ids: list[str]
    rejected_provider_ids: list[tuple[str, str]]
    attempted_provider_ids: list[str]
    fallback_used: bool
    reason: str
    metadata: dict[str, Any]
```

This metadata is useful for:
- Debugging
- Logs
- Tests
- Future observability (M78+)

## Routing Explanation

The routing system is explainable via the `RoutingDecision.reason` field:

**Success:**
```
Selected OpenAI because it supports summarization, is enabled, credentials are configured, it is available, and it has the highest configured priority among eligible providers
```

**Fallback:**
```
No eligible providers available for capability 'summarization' (rejected: openai(unavailable))
```

**AI Disabled:**
```
AI is disabled
```

## Failure-Aware Fallback

M77 uses M76's normalized error categories. The `ProviderManager.generate()` method:

1. Gets a routing decision with ordered candidate providers
2. Attempts each provider in order
3. On failure, records metrics and continues to the next provider
4. Returns the first successful response
5. Raises `ExternalServiceError` if all providers fail

Failure types that trigger fallback:
- `AITransientError` — 5xx, connection errors
- `AIRateLimitError` — 429 rate limits
- `AITimeoutError` — Request timeouts
- `AIAuthenticationError` — Auth failures (safe fallback, no retry loop)

Invalid requests (`AIInvalidResponseError`, `AIPermanentProcessingError`) are not retried with other providers — they represent application-level errors that won't be fixed by switching providers.

## Bounded Fallback

Fallback is strictly bounded:

- Each provider may be attempted at most once per gateway request
- No provider appears twice in `attempted_provider_ids`
- No circular fallback (A → B → A)
- Maximum attempts ≤ number of eligible providers

## Celery Safety

The routing system works correctly from:
- FastAPI requests
- Application use cases
- Celery tasks

No global mutable routing state is introduced. No global async clients reproduce the M42 event-loop problem. Provider adapters retain safe lifecycle behavior.

## Provider Priority Configuration

Provider priorities are configurable via environment variables:

| Provider | Environment Variable | Default |
|----------|---------------------|---------|
| OpenAI | `OPENAI_PRIORITY` | 1 |
| Anthropic | `ANTHROPIC_PRIORITY` | 2 |
| Gemini | `GEMINI_PRIORITY` | 3 |
| Grok | `XAI_PRIORITY` | 4 |

Lower numbers indicate higher priority. The exact values can be tuned per deployment.

## Default Routing

The default routing behavior:

1. All providers advertising the requested capability are candidates
2. Providers are filtered by eligibility (enabled, available, capable)
3. The highest-priority eligible provider is selected
4. On failure, the next eligible provider is attempted
5. If all providers fail, an `ExternalServiceError` is raised

## AI Disabled Behavior

When `AI_ENABLED=false`:
- The routing layer does not call any provider
- No external requests are made
- No API keys are required
- No provider initialization performs external calls
- No hidden fallback to an AI provider occurs
- Existing application fallback behavior is preserved

## Security

- No secrets are logged
- No API keys are exposed through routing decisions
- No raw provider errors containing secrets are returned
- Prompt-injection protections are preserved
- Public users cannot arbitrarily force provider usage (preference is an internal routing parameter)
- Provider selection is an infrastructure concern, not exposed via public API

## Observability

Safe fields logged:
- `capability`
- `selected_provider`
- `attempted_providers`
- `failure_category`
- `fallback_used`
- `duration`

NOT logged:
- API keys
- Authorization headers
- Full prompts
- Full article contents
- Raw provider responses
- Secrets

## Testing

New tests added:
- `tests/unit/application/ai/test_provider_manager_routing.py` — 23 routing tests
- Updated `tests/unit/application/ai/test_provider_manager.py` — 4 tests
- Updated `tests/unit/application/use_cases/article/test_summarize_article.py`
- Updated `tests/unit/application/use_cases/article/test_categorize_article.py`
- Updated `tests/unit/application/use_cases/article/test_analyze_article.py`

All routing tests use mocks. No real provider credentials are required.

## Dependencies

- **No new dependencies added.**

## Files Changed

### New Files
- `tests/unit/application/ai/test_provider_manager_routing.py`

### Modified Files
- `src/ai_news_digest/application/ai/provider_manager.py`
- `src/ai_news_digest/application/ai/models.py`
- `src/ai_news_digest/application/use_cases/article/summarize_article.py`
- `src/ai_news_digest/application/use_cases/article/categorize_article.py`
- `src/ai_news_digest/application/use_cases/article/analyze_article.py`
- `src/ai_news_digest/bootstrap/container.py`
- `tests/unit/application/ai/test_provider_manager.py`
- `tests/unit/application/use_cases/article/test_summarize_article.py`
- `tests/unit/application/use_cases/article/test_categorize_article.py`
- `tests/unit/application/use_cases/article/test_analyze_article.py`

## What M77 Does NOT Implement

M77 deliberately does NOT implement:

- **Circuit breakers** (M78)
- **Persistent provider health scoring** (M78)
- **Quota accounting** (M79)
- **Provider billing/cost optimization** (M79)
- **Token-price optimization** (M79)
- **Free-tier quota tracking** (M79)
- **Budget enforcement** (M79)
- **Cost-based provider ranking** (M79)
- **AI quality benchmarking** (M80)
- **Quality score learning** (M80)
- **Benchmark datasets** (M80)
- **Automatic quality-based routing** (M80)
- **Evidence intelligence** (M81+)
- **Claim traceability** (M81+)
- **Contradiction detection** (M81+)
- **Story timelines** (M81+)
- **Breaking-story detection** (M81+)
- **Trends** (M81+)
- **Personalization** (M81+)
- **Competitive intelligence** (M81+)
- **Intelligence graphs** (M81+)
- **Dashboards** (M81+)

## Next Milestone

**M78 — Provider Health, Failure Tracking & Circuit Breakers**

M78 will add:
- Persistent provider health scoring
- Circuit breaker state
- Automatic provider quarantine
- Failure-rate based routing
- Sophisticated health windows
