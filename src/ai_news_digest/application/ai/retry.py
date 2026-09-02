from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ai_news_digest.application.ai.errors import (
    AIPermanentProcessingError,
    AITransientError,
)
from ai_news_digest.application.ai.models import AIResponse

TransientClassifier = Callable[[Exception], bool]


def _default_transient_classifier(exc: Exception) -> bool:
    """Classify an exception as transient (retryable) or permanent.

    Only errors explicitly modeled as transient are retried. All other
    AIError subclasses (auth, config, rate-limit, timeout, invalid response,
    unsupported) are treated as permanent and raised immediately.
    """
    return isinstance(exc, AITransientError)


def _is_transient(exc: Exception) -> bool:
    return _default_transient_classifier(exc)


class RetryPolicy:
    """Bounded retry policy for transient AI provider failures.

    Uses exponential backoff and never blocks the async event loop because
    tenacity's AsyncRetrying drives the coroutine with asyncio sleeps.
    """

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_delay = max_delay

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> AIResponse:
        """Run *func* through the retry loop, retrying only transient errors.

        Transient errors are retried up to ``max_attempts`` times. All other
        exceptions are re-raised immediately without retry or wrapping, so the
        caller can map them to the appropriate application error type.
        """
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._max_attempts),
                wait=wait_exponential(multiplier=self._base_delay, max=self._max_delay),
                retry=retry_if_exception_type(AITransientError),
                reraise=True,
                before_sleep=_log_retry_attempt,
            ):
                with attempt:
                    return cast(AIResponse, await func(*args, **kwargs))
        except AITransientError:
            raise
        except Exception:
            raise

        raise AIPermanentProcessingError("Retry policy exhausted without a result.")


def _log_retry_attempt(retry_state: RetryCallState) -> None:
    """Emit a structured log before each retry sleep."""
    from ai_news_digest.core.logging import get_logger

    logger = get_logger(__name__)
    attempt_number = retry_state.attempt_number
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "Retrying transient AI provider failure",
        attempt=attempt_number,
        error=str(exc) if exc else None,
    )


__all__ = [
    "RetryPolicy",
    "TransientClassifier",
    "_default_transient_classifier",
]
