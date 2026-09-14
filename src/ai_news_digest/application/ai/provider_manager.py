from __future__ import annotations

import time
from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from ai_news_digest.application.ai.capability_registry import CapabilityRegistry
from ai_news_digest.application.ai.cost import estimate_request_cost
from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponse,
    RoutingDecision,
)
from ai_news_digest.application.ai.provider_health import (
    classify_failure,
)
from ai_news_digest.application.ai.provider_health_registry import ProviderHealthRegistry
from ai_news_digest.application.ai.provider_quota_registry import ProviderQuotaRegistry
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.application.ai.providers.base import AIProvider
from ai_news_digest.application.ai.quota import (
    GlobalBudgetState,
    ProviderUsage,
)
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.core.logging import get_logger
from ai_news_digest.core.metrics import (
    record_ai_failure,
    record_ai_latency,
    record_ai_request,
)

logger = get_logger(__name__)


class ProviderManager:
    """Dynamic AI provider gateway with capability-aware routing and bounded fallback."""

    def __init__(
        self,
        registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
        health_registry: ProviderHealthRegistry | None = None,
        quota_registry: ProviderQuotaRegistry | None = None,
    ) -> None:
        self._registry = registry
        self._capability_registry = capability_registry
        self._decision_engine = decision_engine
        self._health_registry = health_registry
        self._quota_registry = quota_registry

    async def generate(
        self,
        request: AIRequest,
        capability: str | None = None,
        preferred_provider: str | None = None,
        excluded_providers: Iterable[str] | None = None,
    ) -> AIResponse:
        """Generate a response using the best eligible provider with bounded fallback."""
        decision = await self.route(
            request,
            capability=capability,
            preferred_provider=preferred_provider,
            excluded_providers=excluded_providers,
        )

        if decision.selected_provider_id is None:
            raise ExternalServiceError(decision.reason)

        last_exception: Exception | None = None

        for provider_id in decision.attempted_provider_ids:
            provider = self._registry.get(provider_id)
            provider_name = provider.provider_name
            record_ai_request(provider_name)
            start = time.monotonic()
            try:
                response = await provider.generate(request)
            except Exception as exc:
                record_ai_failure(provider_name)
                last_exception = exc
                await self._record_failure(provider_id, exc)
                await self._release_reservation(provider_id, request)
                continue

            record_ai_latency(provider_name, time.monotonic() - start)
            await self._record_success(provider_id)
            await self._finalize_usage(provider_id, request, response)
            return response

        raise ExternalServiceError("Every AI provider failed.") from last_exception

    async def route(
        self,
        request: AIRequest,
        capability: str | None = None,
        preferred_provider: str | None = None,
        excluded_providers: Iterable[str] | None = None,
    ) -> RoutingDecision:
        """Return a deterministic routing decision for the given request context."""
        settings = get_settings()

        if not settings.ai_enabled:
            return RoutingDecision(
                selected_provider_id=None,
                capability=capability,
                candidate_provider_ids=[],
                rejected_provider_ids=[],
                attempted_provider_ids=[],
                fallback_used=False,
                reason="AI is disabled",
            )

        excluded = set(excluded_providers) if excluded_providers else set()

        candidate_ids = self._resolve_candidate_ids(capability)
        candidates: list[AIProvider] = []
        rejected: list[tuple[str, str]] = []
        quota_exclusions: list[tuple[str, str]] = []
        budget_excluded = False

        global_budget = await self._get_global_budget()
        if global_budget.daily_exhausted or global_budget.monthly_exhausted:
            return RoutingDecision(
                selected_provider_id=None,
                capability=capability,
                candidate_provider_ids=[],
                rejected_provider_ids=[],
                attempted_provider_ids=[],
                fallback_used=False,
                reason="Global AI budget exhausted",
                budget_excluded=True,
            )

        for provider_id in candidate_ids:
            if provider_id in excluded:
                rejected.append((provider_id, "excluded"))
                continue

            provider = self._registry.get(provider_id)
            eligible, reason = await self._check_eligibility(provider, capability, request)
            if not eligible:
                if "_quota_exhausted" in reason or reason.startswith("budget_"):
                    quota_exclusions.append((provider_id, reason))
                else:
                    rejected.append((provider_id, reason))
                continue

            candidates.append(provider)

        preferred_ids = {preferred_provider} if preferred_provider else set()
        candidates.sort(
            key=lambda p: (
                0 if p.id in preferred_ids else 1,
                -p.priority(),
                p.id,
            )
        )

        attempted = [p.id for p in candidates]
        selected_id = candidates[0].id if candidates else None

        if selected_id is None:
            reason_parts = ["No eligible providers available"]
            if capability:
                reason_parts.append(f"for capability '{capability}'")
            if rejected:
                reason_parts.append(
                    f"(rejected: {', '.join(f'{pid}({reason})' for pid, reason in rejected)})"
                )
            if quota_exclusions:
                reason_parts.append(
                    "(quota excluded: "
                    f"{', '.join(f'{pid}({reason})' for pid, reason in quota_exclusions)})"
                )
            if budget_excluded:
                reason_parts.append("(global budget exhausted)")
            return RoutingDecision(
                selected_provider_id=None,
                capability=capability,
                candidate_provider_ids=[],
                rejected_provider_ids=rejected,
                attempted_provider_ids=[],
                fallback_used=False,
                reason="; ".join(reason_parts),
                quota_exclusions=quota_exclusions,
                budget_excluded=budget_excluded,
            )

        reason_parts = [
            f"Selected {candidates[0].name} because it supports "
            f"{capability or 'general capability'}, is enabled, "
            f"credentials are configured, it is available, "
            f"and it has the highest configured priority among eligible providers"
        ]
        return RoutingDecision(
            selected_provider_id=selected_id,
            capability=capability,
            candidate_provider_ids=[p.id for p in candidates],
            rejected_provider_ids=rejected,
            attempted_provider_ids=attempted,
            fallback_used=False,
            reason="".join(reason_parts),
            metadata={"priority": candidates[0].priority()},
            quota_exclusions=quota_exclusions,
            budget_excluded=budget_excluded,
        )

    def _resolve_candidate_ids(self, capability: str | None) -> set[str]:
        """Return provider ids that are candidates for the requested capability."""
        if capability:
            return self._decision_engine.resolve({capability})
        return set(self._registry.names())

    async def _check_eligibility(
        self,
        provider: AIProvider,
        capability: str | None,
        request: AIRequest | None = None,
    ) -> tuple[bool, str]:
        """Check whether a provider is eligible for the current request."""
        if not provider.enabled:
            return False, "disabled"

        if not await provider.available():
            return False, "unavailable"

        if capability and capability not in provider.capabilities:
            return False, "incapable"

        if self._health_registry is not None and not await self._health_registry.is_eligible(
            provider.id
        ):
            return False, "circuit_open"

        if self._quota_registry is not None and request is not None:
            settings = get_settings()
            cost_est = estimate_request_cost(request, provider.provider_config)
            if (
                settings.ai_max_estimated_request_cost > 0
                and cost_est.cost_known
                and cost_est.estimated_cost > settings.ai_max_estimated_request_cost
            ):
                return False, "budget_per_request_exceeded"

            try:
                quota_config = await self._quota_registry.get_provider_quota(provider.id)
            except Exception as exc:
                logger.warning(
                    "Failed to load provider quota", provider_id=provider.id, error=str(exc)
                )
                quota_config = None

            if quota_config is not None:
                for limit in quota_config.limits:
                    eligibility = await self._quota_registry.check_quota_eligibility(
                        provider.id,
                        limit.window,
                        estimated_tokens=cost_est.total_tokens,
                        estimated_cost=cost_est.estimated_cost,
                    )
                    if not eligibility.eligible:
                        return False, eligibility.reason

        return True, "eligible"

    async def _get_global_budget(self) -> GlobalBudgetState:
        if self._quota_registry is None:
            return GlobalBudgetState()
        try:
            return await self._quota_registry.get_global_budget()
        except Exception as exc:
            logger.warning("Failed to get global budget", error=str(exc))
            return GlobalBudgetState()

    def _get_provider_config(self, provider_id: str) -> Any:
        provider = self._registry.get(provider_id)
        return provider.provider_config

    async def _reserve_quota(self, provider_id: str, request: AIRequest) -> None:
        if self._quota_registry is None:
            return
        try:
            config = self._get_provider_config(provider_id)
            cost_est = estimate_request_cost(request, config)
            usage = ProviderUsage(
                provider_id=provider_id,
                request_count=1,
                input_tokens=cost_est.input_tokens,
                output_tokens=cost_est.output_tokens,
                total_tokens=cost_est.total_tokens,
                estimated_cost=Decimal(str(cost_est.estimated_cost)),
                cost_known=cost_est.cost_known,
                usage_known=False,
            )
            await self._quota_registry.record_usage(usage)
        except Exception as exc:
            logger.warning("Failed to reserve quota", provider_id=provider_id, error=str(exc))

    async def _finalize_usage(
        self, provider_id: str, request: AIRequest, response: AIResponse
    ) -> None:
        if self._quota_registry is None:
            return
        try:
            config = self._get_provider_config(provider_id)
            input_cost = float(getattr(config, "input_cost_per_1k_tokens", 0.0) or 0.0)
            output_cost = float(getattr(config, "output_cost_per_1k_tokens", 0.0) or 0.0)
            actual_cost = (
                (response.usage.prompt_tokens / 1000.0) * input_cost
                + (response.usage.completion_tokens / 1000.0) * output_cost
            )
            cost_known = input_cost > 0 or output_cost > 0
            usage = ProviderUsage(
                provider_id=provider_id,
                request_count=1,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                estimated_cost=Decimal(str(actual_cost)),
                cost_known=cost_known,
                usage_known=True,
            )
            await self._quota_registry.record_usage(usage)
            await self._quota_registry.update_global_budget(actual_cost)
        except Exception as exc:
            logger.warning("Failed to finalize usage", provider_id=provider_id, error=str(exc))

    async def _release_reservation(self, provider_id: str, request: AIRequest) -> None:
        if self._quota_registry is None:
            return
        try:
            await self._quota_registry.reset_provider_quota(provider_id)
        except Exception as exc:
            logger.warning("Failed to release reservation", provider_id=provider_id, error=str(exc))

    async def _record_success(self, provider_id: str) -> None:
        if self._health_registry is None:
            return
        try:
            await self._health_registry.record_success(provider_id)
        except Exception as exc:
            logger.warning(
                "Failed to record provider success",
                provider_id=provider_id,
                error=str(exc),
            )

    async def _record_failure(self, provider_id: str, exc: Exception) -> None:
        if self._health_registry is None:
            return
        try:
            category = classify_failure(exc)
            await self._health_registry.record_failure(provider_id, category)
        except Exception as exc2:
            logger.warning(
                "Failed to record provider failure",
                provider_id=provider_id,
                error=str(exc2),
            )

