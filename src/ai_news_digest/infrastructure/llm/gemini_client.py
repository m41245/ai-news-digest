from __future__ import annotations

import time
from typing import Any

import httpx

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

_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _map_gemini_error(exc: Exception, status_code: int | None = None) -> Exception:
    """Translate a Gemini API exception into the application error model.

    Only transient failures (5xx, connection errors) are classified as
    retryable. Authentication, bad-request, rate-limit, timeout, and
    validation errors are permanent and must not be retried.
    """
    if status_code == 401:
        return AIAuthenticationError(f"Gemini authentication failed: {exc}")
    if status_code == 429:
        return AIRateLimitError(f"Gemini rate limit exceeded: {exc}")
    if status_code == 408 or status_code == 504:
        return AITimeoutError(f"Gemini request timed out: {exc}")
    if status_code is not None and 400 <= status_code < 500 and status_code != 429:
        return AIPermanentProcessingError(f"Gemini client error (status={status_code}): {exc}")
    if status_code is not None and 500 <= status_code < 600:
        return AITransientError(f"Gemini server error (status={status_code}): {exc}")
    if isinstance(exc, TimeoutError | httpx.TimeoutException):
        return AITimeoutError(f"Gemini request timed out: {exc}")
    if isinstance(exc, httpx.HTTPStatusError):
        return AITransientError(f"Gemini HTTP error: {exc}")
    if isinstance(exc, ValueError | TypeError):
        return AIInvalidResponseError(f"Invalid Gemini response: {exc}")
    return AITransientError(f"Gemini request failed: {exc}")


class GeminiProvider(AIProvider):
    """Google Gemini API implementation for AI provider interface."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._provider_name = "gemini"
        self._model_name = config.model or "gemini-2.0-flash"
        self._retry_policy = RetryPolicy(
            max_attempts=config.max_retries,
            max_delay=max(10.0, config.timeout),
        )

    # ------------------------------------------------------------------
    # Plugin contract
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        """Immutable identifier used as the registry key."""
        return "gemini"

    @property
    def name(self) -> str:
        """Human-readable plugin name."""
        return "Google Gemini"

    @property
    def version(self) -> str:
        """Plugin version string."""
        return "1.0"

    @property
    def description(self) -> str:
        """Human-readable plugin description."""
        return "Google Gemini API provider for text generation and summarization."

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
        pass

    async def available(self) -> bool:
        """Return True when the provider can currently accept requests."""
        return self._config.enabled and self._config.api_key is not None

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
        return False

    @property
    def supports_json_mode(self) -> bool:
        return True

    @property
    def supports_vision(self) -> bool:
        return True

    @property
    def max_context_tokens(self) -> int:
        return self._config.context_window or 1048576

    async def is_available(self) -> bool:
        """Returns True if the provider can currently accept requests."""
        return await self.available()

    async def _call(self, request: AIRequest) -> AIResponse:
        """Execute a single provider call, mapping HTTP errors to the error model."""
        if not self._config.api_key:
            raise AIConfigurationError("Gemini API key not configured.")

        api_key = self._config.api_key
        url = (
            f"{_GEMINI_API_BASE}/models/{self._model_name}:generateContent"
            f"?key={api_key}"
        )

        start_time = time.time()

        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {"text": request.user_prompt},
                    ],
                }
            ],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }

        if request.response_format == AIResponseFormat.JSON:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self._config.timeout),
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
        except httpx.HTTPStatusError as exc:
            raise _map_gemini_error(exc, status_code=exc.response.status_code) from exc
        except AIError:
            raise
        except Exception as exc:
            raise _map_gemini_error(exc) from exc

        latency_ms = (time.time() - start_time) * 1000

        if response.status_code >= 400:
            raise _map_gemini_error(
                RuntimeError(f"Gemini HTTP error: {response.text}"),
                status_code=response.status_code,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise AIInvalidResponseError(f"Invalid Gemini JSON response: {exc}") from exc

        candidates = data.get("candidates", [])
        if not candidates:
            raise AIInvalidResponseError("Gemini API returned an empty candidates list.")

        content_parts = candidates[0].get("content", {}).get("parts", [])
        text_content = ""
        for part in content_parts:
            if "text" in part:
                text_content = part["text"]
                break

        if not text_content:
            raise AIInvalidResponseError("Gemini response did not contain any text content.")

        usage_meta = data.get("usageMetadata", {})
        prompt_tokens = usage_meta.get("promptTokenCount", 0)
        completion_tokens = usage_meta.get("candidatesTokenCount", 0)
        total_tokens = usage_meta.get("totalTokenCount", prompt_tokens + completion_tokens)

        return AIResponse(
            provider=self._provider_name,
            model=self._model_name,
            content=text_content,
            usage=AIUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            latency_ms=latency_ms,
            metadata=request.metadata,
        )

    async def generate(self, request: AIRequest) -> AIResponse:
        """Execute one AI request using Gemini API with retry handling."""
        try:
            return await self._retry_policy.execute(self._call, request)
        except AIError:
            raise

    async def health_check(self) -> bool:
        """Lightweight connectivity test."""
        if not self._config.api_key:
            return False

        url = (
            f"{_GEMINI_API_BASE}/models/{self._model_name}:generateContent"
            f"?key={self._config.api_key}"
        )
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": "hi"}]}],
            "generationConfig": {"maxOutputTokens": 1},
        }

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(min(self._config.timeout, 10.0)),
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
            return response.status_code < 400
        except Exception:
            return False


__all__ = ["GeminiProvider"]
