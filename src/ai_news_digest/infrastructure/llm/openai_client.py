from __future__ import annotations

import time

from openai import APIConnectionError as OpenAIConnectionError
from openai import APIStatusError as OpenAIStatusError
from openai import APITimeoutError as OpenAPITimeoutError
from openai import AsyncOpenAI
from openai import AuthenticationError as OpenAIAuthError
from openai import RateLimitError as OpenAIRateLimitError
from openai.types.chat.chat_completion_message_param import (
    ChatCompletionMessageParam,
)
from openai.types.chat.chat_completion_system_message_param import (
    ChatCompletionSystemMessageParam,
)
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params.response_format_json_object import (
    ResponseFormatJSONObject,
)

from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.application.ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIError,
    AIInvalidResponseError,
    AIPermanentProcessingError,
    AIRateLimitError,
    AITimeoutError,
    AITransientError,
)
from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponse,
    AIResponseFormat,
    AIUsage,
)
from ai_news_digest.application.ai.providers.base import AIProvider
from ai_news_digest.application.ai.retry import RetryPolicy


def _redact_openai_secret(text: str, api_key: str | None) -> str:
    """Redact a configured OpenAI/Groq secret and common partial forms.

    OpenAI-style errors frequently include only a fragment of the key (for
    example ``sk-...abcd``).  Redact the full key plus derived partial
    representations so credentials cannot leak through exception text.
    """
    if not api_key:
        return text

    redacted = text.replace(api_key, "[REDACTED]")

    # Common suffix-only representations reported by providers.
    for suffix_length in (12, 8, 6, 4):
        if suffix_length < len(api_key):
            suffix = api_key[-suffix_length:]
            if suffix:
                redacted = redacted.replace(suffix, "[REDACTED]")

    # Common ellipsis-style representations such as ``sk-...abcd``.
    for prefix_length in (3, 4, 5, 6, 7, 8):
        for suffix_length in (4, 6, 8):
            if prefix_length + suffix_length < len(api_key):
                prefix = api_key[:prefix_length]
                suffix = api_key[-suffix_length:]
                for separator in ("...", "…", "***", "****", ".."):
                    candidate = f"{prefix}{separator}{suffix}"
                    redacted = redacted.replace(candidate, "[REDACTED]")

    return redacted


def _map_openai_error(
    exc: Exception,
    provider_label: str = "OpenAI",
    api_key: str | None = None,
    status_code: int | None = None,
) -> Exception:
    """Translate an OpenAI SDK exception into the application error model.

    Only transient failures (5xx, connection errors) are classified as
    retryable. Authentication, bad-request, rate-limit, timeout, and
    validation errors are permanent and must not be retried.
    """
    if status_code is None:
        status_code = getattr(exc, "status_code", None)

    redacted = _redact_openai_secret(str(exc), api_key)

    if isinstance(exc, OpenAIAuthError):
        return AIAuthenticationError(f"{provider_label} authentication failed: {redacted}")
    if isinstance(exc, OpenAIRateLimitError):
        return AIRateLimitError(f"{provider_label} rate limit exceeded: {redacted}")
    if isinstance(exc, OpenAPITimeoutError):
        return AITimeoutError(f"{provider_label} request timed out: {redacted}")
    if isinstance(exc, OpenAIStatusError):
        resolved_status = status_code or 500
        if 500 <= resolved_status < 600:
            return AITransientError(
                f"{provider_label} server error (status={resolved_status}): {redacted}"
            )
        return AIPermanentProcessingError(
            f"{provider_label} client error (status={resolved_status}): {redacted}"
        )
    if isinstance(exc, OpenAIConnectionError):
        return AITransientError(f"{provider_label} connection failed: {redacted}")
    if isinstance(exc, ValueError):
        return AIInvalidResponseError(f"Invalid {provider_label} response: {redacted}")
    return AITransientError(f"{provider_label} request failed: {redacted}")


class OpenAIProvider(AIProvider):
    """OpenAI API implementation for AI provider interface."""

    _client: AsyncOpenAI | None

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._provider_name = "openai"
        self._provider_label = "OpenAI"
        self._model_name = config.model or "gpt-4o-mini"
        self._retry_policy = RetryPolicy(
            max_attempts=config.max_retries,
            max_delay=max(10.0, config.timeout),
        )

        if config.api_key:
            self._client = AsyncOpenAI(
                api_key=config.api_key,
                base_url=config.base_url,
                timeout=config.timeout,
                max_retries=0,
            )
        else:
            self._client = None

    # ------------------------------------------------------------------
    # Plugin contract
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        """Immutable identifier used as the registry key."""
        return "openai"

    @property
    def name(self) -> str:
        """Human-readable plugin name."""
        return "OpenAI"

    @property
    def version(self) -> str:
        """Plugin version string."""
        return "1.0"

    @property
    def description(self) -> str:
        """Human-readable plugin description."""
        return "OpenAI API provider for text generation and summarization."

    @property
    def capabilities(self) -> set[str]:
        """Set of capability names exposed by the plugin."""
        return {"summarization", "categorization", "analysis"}

    @property
    def enabled(self) -> bool:
        """Whether the plugin is currently enabled."""
        return self._config.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set the enabled state."""
        self._config.enabled = value

    def initialize(self) -> None:
        """Initialize plugin resources and internal state."""
        pass

    async def shutdown(self) -> None:
        """Release plugin resources and stop background work."""
        if self._client is not None:
            await self._client.close()

    async def available(self) -> bool:
        """Return True when the provider can currently accept requests."""
        return (
            self._config.enabled and self._config.api_key is not None and self._client is not None
        )

    def priority(self) -> int:
        """Return the provider priority used during selection."""
        return self._config.priority

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""
        return self._provider_name

    @property
    def model_name(self) -> str:
        """Active model."""
        return self._model_name

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_json_mode(self) -> bool:
        return True

    @property
    def supports_vision(self) -> bool:
        return True

    @property
    def max_context_tokens(self) -> int:
        return self._config.context_window or 128000

    async def is_available(self) -> bool:
        """Returns True if the provider can currently accept requests."""
        return await self.available()

    async def _call(self, request: AIRequest) -> AIResponse:
        """Execute a single provider call, mapping SDK errors to the error model."""
        if not self._client:
            raise AIConfigurationError(f"{self._provider_label} client not configured.")

        start_time = time.time()

        mapped_error: Exception | None = None
        try:
            messages: list[ChatCompletionMessageParam] = [
                ChatCompletionSystemMessageParam(
                    role="system",
                    content=request.system_prompt,
                ),
                ChatCompletionUserMessageParam(
                    role="user",
                    content=request.user_prompt,
                ),
            ]

            if request.response_format == AIResponseFormat.JSON:
                response = await self._client.chat.completions.create(
                    model=self._model_name,
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    response_format=ResponseFormatJSONObject(type="json_object"),
                )
            else:
                response = await self._client.chat.completions.create(
                    model=self._model_name,
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                )
        except AIError:
            raise
        except Exception as exc:
            mapped_error = _map_openai_error(
                exc,
                provider_label=self._provider_label,
                api_key=self._config.api_key,
            )
            mapped_error.__cause__ = None
            mapped_error.__context__ = None
            mapped_error.__suppress_context__ = True

        if mapped_error is not None:
            raise mapped_error

        latency_ms = (time.time() - start_time) * 1000

        if not response.choices:
            raise AIInvalidResponseError(
                f"{self._provider_label} API returned an empty choices list."
            )

        if response.usage is not None:
            usage = AIUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
        else:
            usage = AIUsage()

        return AIResponse(
            provider=self._provider_name,
            model=self._model_name,
            content=response.choices[0].message.content or "",
            usage=usage,
            latency_ms=latency_ms,
            metadata=request.metadata,
        )

    async def generate(self, request: AIRequest) -> AIResponse:
        """Execute one AI request using OpenAI API with retry handling."""
        try:
            return await self._retry_policy.execute(self._call, request)
        except AIError:
            raise

    async def health_check(self) -> bool:
        """Lightweight connectivity test."""
        if not self._client:
            return False

        try:
            await self._client.models.list()
            return True
        except Exception:
            return False


__all__ = ["OpenAIProvider"]
