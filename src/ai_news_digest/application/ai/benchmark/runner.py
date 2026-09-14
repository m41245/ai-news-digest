"""
Benchmark execution engine for M80.

Provides a deterministic, bounded, fail-safe benchmark runner that
integrates with existing M79 provider abstractions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ai_news_digest.application.ai.benchmark.dataset import load_dataset
from ai_news_digest.application.ai.benchmark.evaluator import BenchmarkEvaluator, EvaluationContext
from ai_news_digest.application.ai.benchmark.models import (
    BenchmarkCase,
    BenchmarkDataset,
    BenchmarkFailureInfo,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkTask,
    FailureCategory,
)
from ai_news_digest.application.ai.provider_manager import ProviderManager
from ai_news_digest.application.ai.providers.base import AIProvider
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class BenchmarkExecutionConfig:
    """Configuration for a benchmark run."""

    provider_ids: tuple[str, ...] = ()
    model_ids: tuple[str, ...] = ()
    case_ids: tuple[str, ...] = ()
    task_ids: tuple[str, ...] = ()
    max_providers: int = 4
    max_cases: int = 10
    max_tasks: int = 7
    max_total_requests: int = 50
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.max_providers < 1:
            raise ValueError("max_providers must be >= 1.")
        if self.max_cases < 1:
            raise ValueError("max_cases must be >= 1.")
        if self.max_tasks < 1:
            raise ValueError("max_tasks must be >= 1.")
        if self.max_total_requests < 1:
            raise ValueError("max_total_requests must be >= 1.")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0.")


class BenchmarkRunner:
    """Deterministic benchmark execution engine.

    Respects AI_ENABLED, provider eligibility, circuit breakers, quotas,
    and global budget through the existing ProviderManager.
    """

    def __init__(
        self,
        provider_manager: ProviderManager,
        registry: Any,
        config: BenchmarkExecutionConfig | None = None,
        dataset: BenchmarkDataset | None = None,
    ) -> None:
        self._provider_manager = provider_manager
        self._registry = registry
        self._config = config or BenchmarkExecutionConfig()
        self._dataset = dataset or load_dataset()
        self._evaluator = BenchmarkEvaluator()

    async def run(self) -> BenchmarkRun:
        """Execute the benchmark run."""
        settings = get_settings()

        if not settings.ai_enabled:
            run = BenchmarkRun(
                run_id=_make_run_id(),
                dataset_version=self._dataset.version,
                benchmark_version="m80-v1",
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                config=self._config_to_dict(),
            )
            run.results.append(
                BenchmarkResult(
                    provider_id="system",
                    model="none",
                    case_id="ai_disabled",
                    task=BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY,
                    failure=BenchmarkFailureInfo(
                        provider_id="system",
                        model="none",
                        case_id="ai_disabled",
                        task=BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY,
                        category=FailureCategory.UNAVAILABLE,
                        error_message="AI is disabled (AI_ENABLED=false).",
                    ),
                )
            )
            run.total_requests = 1
            run.failures = 1
            return run

        provider_ids = self._resolve_provider_ids()
        case_ids = self._resolve_case_ids()
        task_ids = self._resolve_task_ids()

        run = BenchmarkRun(
            run_id=_make_run_id(),
            dataset_version=self._dataset.version,
            benchmark_version="m80-v1",
            started_at=datetime.now(UTC),
            config=self._config_to_dict(),
            provider_ids=tuple(provider_ids),
            case_ids=tuple(case_ids),
            task_ids=tuple(task_ids),
        )

        request_count = 0
        for provider_id in provider_ids:
            if request_count >= self._config.max_total_requests:
                break
            provider = self._registry.get(provider_id)
            for case in self._dataset.cases:
                if case.case_id not in case_ids:
                    continue
                if case.task not in task_ids:
                    continue
                if request_count >= self._config.max_total_requests:
                    break

                result = await self._execute_case(provider, case)
                run.results.append(result)
                request_count += 1

        run.total_requests = len(run.results)
        run.successes = sum(1 for r in run.results if r.failure is None)
        run.failures = run.total_requests - run.successes
        run.completed_at = datetime.now(UTC)
        return run

    async def _execute_case(self, provider: AIProvider, case: BenchmarkCase) -> BenchmarkResult:
        start = time.monotonic()
        try:
            response = await self._provider_manager.generate(
                _build_ai_request(case),
                capability="summarization",
                preferred_provider=provider.id,
            )
            latency_ms = (time.monotonic() - start) * 1000.0

            parsed = _safe_parse(response.content)
            context = EvaluationContext(
                case=case,
                provider_id=provider.id,
                model=provider.model_name,
                raw_content=response.content,
                parsed_structured=parsed,
                latency_ms=latency_ms,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                estimated_cost=response.estimated_cost,
                cost_known=response.cost_known,
                usage_known=True,
                metadata=response.metadata,
            )
            return self._evaluator.evaluate(context)
        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000.0
            category = _classify_failure(exc)
            return BenchmarkResult(
                provider_id=provider.id,
                model=provider.model_name,
                case_id=case.case_id,
                task=case.task,
                latency_ms=latency_ms,
                failure=BenchmarkFailureInfo(
                    provider_id=provider.id,
                    model=provider.model_name,
                    case_id=case.case_id,
                    task=case.task,
                    category=category,
                    error_message=str(exc)[:500],
                    latency_ms=latency_ms,
                    timestamp=datetime.now(UTC),
                ),
            )

    def _resolve_provider_ids(self) -> list[str]:
        all_ids = list(self._registry.names())
        selected = [pid for pid in self._config.provider_ids if pid in all_ids]
        if not selected:
            selected = all_ids[: self._config.max_providers]
        return selected[: self._config.max_providers]

    def _resolve_case_ids(self) -> list[str]:
        all_cases = [c.case_id for c in self._dataset.cases]
        selected = [cid for cid in self._config.case_ids if cid in all_cases]
        if not selected:
            selected = all_cases[: self._config.max_cases]
        return selected[: self._config.max_cases]

    def _resolve_task_ids(self) -> list[BenchmarkTask]:
        all_tasks = sorted({t.value for t in BenchmarkTask})
        selected = [t for t in self._config.task_ids if t in all_tasks]
        if not selected:
            selected = all_tasks[: self._config.max_tasks]
        return [BenchmarkTask(t) for t in selected[: self._config.max_tasks]]

    def _config_to_dict(self) -> dict[str, Any]:
        return {
            "provider_ids": list(self._config.provider_ids),
            "model_ids": list(self._config.model_ids),
            "case_ids": list(self._config.case_ids),
            "task_ids": list(self._config.task_ids),
            "max_providers": self._config.max_providers,
            "max_cases": self._config.max_cases,
            "max_tasks": self._config.max_tasks,
            "max_total_requests": self._config.max_total_requests,
            "timeout_seconds": self._config.timeout_seconds,
        }


def _make_run_id() -> str:
    return f"benchmark-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"


def _build_ai_request(case: BenchmarkCase) -> Any:
    from ai_news_digest.application.ai.models import AIRequest, AIResponseFormat

    return AIRequest(
        system_prompt="You are an AI news analysis assistant. Output structured JSON only.",
        user_prompt=(
            f"Analyze the following article and produce structured output.\n\n"
            f"Title: {case.article_title}\n\n"
            f"Content:\n{case.article_content}"
        ),
        temperature=0.2,
        max_tokens=1024,
        response_format=AIResponseFormat.JSON,
        metadata={"benchmark_case_id": case.case_id, "task": case.task.value},
    )


def _safe_parse(raw: str) -> dict[str, Any] | None:
    try:
        import json

        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        logger.debug("Failed to parse benchmark response as JSON", exc_info=True)
    return None


def _classify_failure(exc: BaseException) -> FailureCategory:
    from ai_news_digest.application.ai.errors import (
        AIAuthenticationError,
        AIInvalidResponseError,
        AIQuotaExhaustedError,
        AIRateLimitError,
        AITimeoutError,
        AITransientError,
        AIUnsupportedProviderError,
    )

    if isinstance(exc, AITimeoutError):
        return FailureCategory.TIMEOUT
    if isinstance(exc, AIRateLimitError):
        return FailureCategory.RATE_LIMIT
    if isinstance(exc, AIAuthenticationError):
        return FailureCategory.AUTHENTICATION
    if isinstance(exc, AIInvalidResponseError):
        return FailureCategory.INVALID_RESPONSE
    if isinstance(exc, AIQuotaExhaustedError):
        return FailureCategory.UNAVAILABLE
    if isinstance(exc, AITransientError):
        return FailureCategory.UNAVAILABLE
    if isinstance(exc, AIUnsupportedProviderError):
        return FailureCategory.INVALID_RESPONSE
    return FailureCategory.UNKNOWN_PROVIDER_ERROR


__all__ = [
    "BenchmarkExecutionConfig",
    "BenchmarkRunner",
]
