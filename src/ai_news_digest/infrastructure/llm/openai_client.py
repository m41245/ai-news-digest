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


def _map_openai_error(exc: Exception) -> Exception:
    """Translate an OpenAI SDK exception into the application error model.

    Only transient failures (5xx, connection errors) are classified as
    retryable. Authentication, bad-request, rate-limit, timeout, and
    validation errors are permanent and must not be retried.
    """
    if isinstance(exc, OpenAIAuthError):
        return AIAuthenticationError(f"OpenAI authentication failed: {exc}")
    if isinstance(exc, OpenAIRateLimitError):
        return AIRateLimitError(f"OpenAI rate limit exceeded: {exc}")
    if isinstance(exc, OpenAPITimeoutError):
        return AITimeoutError(f"OpenAI request timed out: {exc}")
    if isinstance(exc, OpenAIStatusError):
        status_code = getattr(exc, "status_code", None) or 500
        if 500 <= status_code < 600:
            return AITransientError(f"OpenAI server error (status={status_code}): {exc}")
        return AIPermanentProcessingError(f"OpenAI client error (status={status_code}): {exc}")
    if isinstance(exc, OpenAIConnectionError):
        return AITransientError(f"OpenAI connection failed: {exc}")
    if isinstance(exc, ValueError):
        return AIInvalidResponseError(f"Invalid OpenAI response: {exc}")
    return AITransientError(f"OpenAI request failed: {exc}")


class OpenAIProvider(AIProvider):
    """OpenAI API implementation for AI provider interface."""

    _client: AsyncOpenAI | None

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._provider_name = "openai"
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
        return {"summarization", "categorization"}

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
            raise AIConfigurationError("OpenAI client not configured.")

        start_time = time.time()

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
            raise _map_openai_error(exc) from exc

        latency_ms = (time.time() - start_time) * 1000

        if not response.choices:
            raise AIInvalidResponseError("OpenAI API returned an empty choices list.")

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
