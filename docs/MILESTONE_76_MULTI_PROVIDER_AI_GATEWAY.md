# Milestone 76 — Multi-Provider AI Gateway & Provider Abstraction Foundation

## Status: COMPLETE

## Architecture

```
Application
    ↓
AI Gateway (ProviderManager)
    ↓
Provider Registry (ProviderRegistry)
    ↓
Provider Adapter (OpenAI / Anthropic / Gemini / Grok)
    ↓
External AI Provider
```

## What Changed

M76 established the clean provider-neutral architecture required for multi-provider AI support. The existing M70 provider abstraction was already well-structured with `Plugin`, `AIProvider`, `ProviderRegistry`, `CapabilityRegistry`, `DecisionEngine`, and `ProviderManager`. M76 extended this foundation by:

1. Adding a **Gemini provider adapter** using `httpx` (already a project dependency)
2. Adding a **Grok/xAI provider adapter** reusing the existing `openai` SDK with a custom `base_url`
3. Extending `LLMProviderFactory` to construct all four providers
4. Extending `Container._configure_providers` to register Gemini and Grok
5. Adding provider-specific settings to `core/config.py`
6. Updating `.env.example` and `render.yaml` with new environment variables
7. Adding comprehensive contract tests for both new providers
8. Adding container registration tests for all four providers

## Provider Contract

All providers implement the existing `AIProvider` interface:

```python
class AIProvider(Plugin, ABC):
    @abstractmethod
    async def available(self) -> bool: ...
    @abstractmethod
    def priority(self) -> int: ...
    @property
    @abstractmethod
    def provider_name(self) -> str: ...
    @property
    @abstractmethod
    def model_name(self) -> str: ...
    @property
    @abstractmethod
    def supports_streaming(self) -> bool: ...
    @property
    @abstractmethod
    def supports_json_mode(self) -> bool: ...
    @property
    @abstractmethod
    def supports_vision(self) -> bool: ...
    @property
    @abstractmethod
    def max_context_tokens(self) -> int: ...
    @abstractmethod
    async def generate(self, request: AIRequest) -> AIResponse: ...
    @abstractmethod
    async def health_check(self) -> bool: ...
```

## Providers

| Provider | ID | Adapter Location | SDK | Status |
|----------|----|------------------|-----|--------|
| OpenAI | `openai` | `infrastructure/llm/openai_client.py` | `openai` | Configured, tested |
| Anthropic | `anthropic` | `infrastructure/llm/anthropic_client.py` | `anthropic` | Configured, tested |
| Google Gemini | `gemini` | `infrastructure/llm/gemini_client.py` | `httpx` (REST) | Available, tested via mocks |
| xAI Grok | `grok` | `infrastructure/llm/grok_client.py` | `openai` (custom base_url) | Available, tested via mocks |

## Configuration

New environment variables:

```env
# Google Gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_ENABLED=false
GEMINI_MODEL=gemini-2.0-flash
GEMINI_PRIORITY=3
GEMINI_TIMEOUT=30
GEMINI_MAX_RETRIES=3

# xAI Grok
XAI_API_KEY=your_xai_api_key_here
XAI_ENABLED=false
XAI_MODEL=grok-2-latest
XAI_PRIORITY=4
XAI_TIMEOUT=30
XAI_MAX_RETRIES=3
```

Updated `DEFAULT_LLM_PROVIDER` literal now accepts `gemini` and `grok`.

## Failure Normalization

All providers translate their native exceptions into the application's error model:

| Native Failure | Normalized Error |
|----------------|------------------|
| Auth failure | `AIAuthenticationError` |
| Rate limit | `AIRateLimitError` |
| Timeout | `AITimeoutError` |
| Server error (5xx) | `AITransientError` |
| Client error (4xx) | `AIPermanentProcessingError` |
| Connection failure | `AITransientError` |
| Invalid/malformed response | `AIInvalidResponseError` |

## Capability Matching

Providers advertise capabilities via the `Plugin.capabilities` property:

- `summarization`
- `categorization`
- `analysis`

The `DecisionEngine` resolves providers by intersecting required capabilities. The `ProviderManager` selects the highest-priority available provider with automatic fallback to the next eligible provider on transient failures.

## AI Safety

- `AI_ENABLED=false` remains the default
- Missing credentials result in `available() == False`, not application crash
- No API keys are logged
- No secrets are exposed through API responses
- Structured output is validated before persistence
- Prompt-injection protections are preserved

## Celery Compatibility

Providers use the existing `RetryPolicy` (tenacity) for bounded retry of transient failures. The `ProviderManager` fallback is simple and deterministic. No global async client state is shared across tasks. Worker lifecycle is safe.

## Testing

New tests added:

- `tests/unit/infrastructure/llm/test_gemini_client.py` — 16 tests
- `tests/unit/infrastructure/llm/test_grok_client.py` — 17 tests
- `tests/unit/bootstrap/test_container.py` — 3 new provider registration tests + 1 multi-provider SecretStr test

All provider tests use mocks. No real provider credentials are required.

## What M76 Does NOT Implement

M76 deliberately does NOT implement:

- **Advanced dynamic routing** (M77)
- **Circuit breakers** (M78)
- **Cost/quota-aware routing** (M79)
- **AI quality benchmarking** (M80)
- **Provider health scoring**
- **Evidence intelligence**
- **Contradiction detection**
- **Timeline intelligence**
- **Trend detection**
- **Personalization**
- **Competitive intelligence**
- **Intelligence graph**
- **Scoreboard**
- **Advanced dashboard**

## Dependencies

- **No new dependencies added.** Gemini uses the existing `httpx` client. Grok reuses the existing `openai` SDK with a custom `base_url`.

## Files Changed

### New Files
- `src/ai_news_digest/infrastructure/llm/gemini_client.py`
- `src/ai_news_digest/infrastructure/llm/grok_client.py`
- `tests/unit/infrastructure/llm/test_gemini_client.py`
- `tests/unit/infrastructure/llm/test_grok_client.py`
- `docs/MILESTONE_76_MULTI_PROVIDER_AI_GATEWAY.md`

### Modified Files
- `src/ai_news_digest/infrastructure/llm/factory.py`
- `src/ai_news_digest/bootstrap/container.py`
- `src/ai_news_digest/core/config.py`
- `.env.example`
- `render.yaml`
- `tests/unit/bootstrap/test_container.py`

## Security

- No secrets committed
- AI remains disabled by default (`AI_ENABLED=false`)
- Provider credentials are environment-based
- No sensitive payloads logged
- Prompt-injection protections remain intact

## Next Milestone

**M77 — Dynamic Provider Routing**

M77 will implement capability-aware provider selection with latency tracking, cost estimation, and quality-weighted routing. M76 establishes the clean abstraction layer that M77 builds upon.
