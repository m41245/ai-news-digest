from __future__ import annotations

import hashlib
import time
import uuid
from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from ai_news_digest.application.ai.capability_registry import CapabilityRegistry
from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.application.ai.cost import estimate_request_cost
from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.free_models import (
    FREE_PROVIDER_MODEL_ALLOWLIST,
    is_allowlisted_free_model,
    is_free_only_mode,
)
from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponse,
    RoutingDecision,
)
from ai_news_digest.application.ai.provider_health import (
    FailureCategory,
    classify_failure,
)
from ai_news_digest.application.ai.provider_health_registry import ProviderHealthRegistry
from ai_news_digest.application.ai.provider_quota_registry import ProviderQuotaRegistry
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.application.ai.providers.base import AIProvider
from ai_news_digest.application.ai.quota import (
    GlobalBudgetState,
    ProviderQuotaConfig,
    ProviderUsage,
    QuotaLimit,
    QuotaReservationRequest,
    QuotaReservationResult,
    QuotaWindow,
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


def build_quota_config_from_provider_config(
    provider_id: str,
    config: ProviderConfig,
) -> ProviderQuotaConfig | None:
    """Build a :class:`ProviderQuotaConfig` from a provider's settings config.

    Settings express 0 (or 0.0) as "no limit" / unlimited. This maps a
    zero limit to ``None`` so that an absent limit is never interpreted as
    an arbitrary positive cap. Returns ``None`` when no limit is configured,
    leaving the provider without quota enforcement from settings.

    The DAY window is used because provider settings expose a single value
    per dimension (no window selector) and daily usage is the primary
    accounting window recorded by :class:`ProviderUsage`.
    """
    request_limit = config.request_limit if config.request_limit > 0 else None
    token_limit = config.token_limit if config.token_limit > 0 else None
    cost_limit = Decimal(str(config.cost_limit)) if config.cost_limit > 0 else None
    if request_limit is None and token_limit is None and cost_limit is None:
        return None
    return ProviderQuotaConfig(
        provider_id=provider_id,
        limits=[
            QuotaLimit(
                window=QuotaWindow.DAY,
                request_limit=request_limit,
                token_limit=token_limit,
                cost_limit=cost_limit,
            )
        ],
    )


class ProviderManager:
    """Dynamic AI provider gateway with capability-aware routing and bounded fallback."""

    def __init__(
        self,
        registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
        health_registry: ProviderHealthRegistry | None = None,
        quota_registry: ProviderQuotaRegistry | None = None,
        free_only: bool | None = None,
    ) -> None:
        self._registry = registry
        self._capability_registry = capability_registry
        self._decision_engine = decision_engine
        self._health_registry = health_registry
        self._quota_registry = quota_registry
        self._free_only = free_only if free_only is not None else is_free_only_mode()

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

            reservation_id = self._generate_reservation_id(provider_id, request)
            reservation = await self._reserve_capacity(provider_id, request, reservation_id)

            if reservation is not None and not reservation.reserved:
                record_ai_failure(provider_name)
                if reservation.budget_exceeded:
                    logger.info(
                        "Provider skipped: reservation rejected",
                        provider_id=provider_id,
                        reason=reservation.reason,
                    )
                else:
                    logger.warning(
                        "Provider skipped: reservation failed",
                        provider_id=provider_id,
                        reason=reservation.reason,
                    )
                last_exception = ExternalServiceError(
                    f"Capacity reservation failed for provider '{provider_id}': "
                    f"{reservation.reason}"
                )
                continue

            try:
                response = await provider.generate(request)
            except Exception as exc:
                record_ai_failure(provider_name)
                last_exception = exc
                await self._record_failure(provider_id, exc)
                if reservation is not None:
                    await self._handle_provider_failure(provider_id, reservation_id, exc)
                continue

            record_ai_latency(provider_name, time.monotonic() - start)
            await self._record_success(provider_id)
            if reservation is not None:
                await self._settle_reservation(provider_id, request, response, reservation_id)
            return response

        if last_exception is not None:
            raise ExternalServiceError(
                f"Every AI provider failed: {last_exception}"
            ) from last_exception
        raise ExternalServiceError("Every AI provider failed.")

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
        if global_budget.budget_read_failed and (
            global_budget.daily_budget > 0 or global_budget.monthly_budget > 0
        ):
            return RoutingDecision(
                selected_provider_id=None,
                capability=capability,
                candidate_provider_ids=[],
                rejected_provider_ids=[],
                attempted_provider_ids=[],
                fallback_used=False,
                reason="Global AI budget unavailable (quota store failure)",
                budget_excluded=True,
            )
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

        if (
            self._free_only or provider.id in FREE_PROVIDER_MODEL_ALLOWLIST
        ) and not is_allowlisted_free_model(provider.id, getattr(provider, "model_name", None)):
            return False, "non_allowlisted_model"

        if self._health_registry is not None and not await self._health_registry.is_eligible(
            provider.id
        ):
            return False, "circuit_open"

        if request is None:
            return True, "eligible"

        settings = get_settings()
        provider_config = provider.provider_config

        # Per-request estimated-cost cap: a hard guard sourced from settings.
        # Enforced independently of the quota registry so the ceiling still
        # applies when Redis (usage accounting) is unavailable.
        cost_est = None
        if settings.ai_max_estimated_request_cost > 0:
            cost_est = estimate_request_cost(request, provider_config)
            if not cost_est.cost_known:
                return False, "budget_per_request_cost_unknown"
            if cost_est.estimated_cost > settings.ai_max_estimated_request_cost:
                return False, "budget_per_request_exceeded"

        if self._quota_registry is None:
            return True, "eligible"

        if cost_est is None:
            cost_est = estimate_request_cost(request, provider_config)

        # Per-provider limits. Settings (ProviderConfig) are the authoritative
        # source of limit configuration; an explicitly administered Redis quota
        # (get_provider_quota) takes precedence and overrides settings. Live
        # usage accounting remains in Redis via check_quota_eligibility.
        try:
            quota_config = await self._quota_registry.get_provider_quota(provider.id)
        except Exception as exc:
            logger.warning("Failed to load provider quota", provider_id=provider.id, error=str(exc))
            quota_config = None

        if quota_config is None and isinstance(provider_config, ProviderConfig):
            quota_config = build_quota_config_from_provider_config(provider.id, provider_config)

        if quota_config is not None and quota_config.limits:
            for limit in quota_config.limits:
                try:
                    eligibility = await self._quota_registry.check_quota_eligibility(
                        provider.id,
                        limit.window,
                        estimated_tokens=cost_est.total_tokens,
                        estimated_cost=cost_est.estimated_cost,
                        limit=limit,
                    )
                except Exception as exc:
                    logger.warning(
                        "Quota check raised",
                        provider_id=provider.id,
                        error=str(exc),
                    )
                    return False, "budget_quota_check_failed"
                if not eligibility.eligible:
                    return False, eligibility.reason
                if eligibility.reason in ("quota_check_failed", "unknown_check_result"):
                    return False, "budget_quota_check_failed"

        return True, "eligible"

    async def _get_global_budget(self) -> GlobalBudgetState:
        if self._quota_registry is None:
            return GlobalBudgetState()
        try:
            state = await self._quota_registry.get_global_budget()
        except Exception as exc:
            logger.warning("Failed to get global budget", error=str(exc))
            state = GlobalBudgetState(budget_read_failed=True)
        settings = get_settings()
        # Settings are the authoritative source for configured budgets; Redis
        # holds live spend accounting. A non-zero Redis budget (explicitly
        # administered) takes precedence over settings; a zero/unset Redis
        # budget falls back to the settings value. This avoids overwriting an
        # administrated budget while still making plain configuration effective.
        daily_budget = (
            state.daily_budget
            if state.daily_budget > 0
            else Decimal(str(settings.ai_daily_cost_budget))
        )
        monthly_budget = (
            state.monthly_budget
            if state.monthly_budget > 0
            else Decimal(str(settings.ai_monthly_cost_budget))
        )
        return GlobalBudgetState(
            daily_budget=daily_budget,
            monthly_budget=monthly_budget,
            daily_spend=state.daily_spend,
            monthly_spend=state.monthly_spend,
            updated_at=state.updated_at,
            budget_read_failed=state.budget_read_failed,
        )

    def _get_provider_config(self, provider_id: str) -> Any:
        provider = self._registry.get(provider_id)
        return provider.provider_config

    def _generate_reservation_id(self, provider_id: str, request: AIRequest) -> str:
        """Generate a stable, deterministic reservation identifier.

        Reuses ``metadata['request_id']`` when present, otherwise derives a
        fingerprint from the request content.  The ID is namespaced by
        provider and quota window so that retries of the same request to
        the same provider remain idempotent while genuinely separate
        provider attempts receive distinct reservations.
        """
        request_ref = request.metadata.get("request_id") if request.metadata else None
        if not request_ref:
            content = f"{request.system_prompt}:{request.user_prompt}:{request.max_tokens}"
            request_ref = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        return str(
            uuid.uuid5(uuid.NAMESPACE_DNS, f"{provider_id}:{request_ref}:{QuotaWindow.DAY.value}")
        )

    async def _reserve_capacity(
        self,
        provider_id: str,
        request: AIRequest,
        reservation_id: str,
    ) -> QuotaReservationResult | None:
        """Atomically check limits and reserve capacity for a provider request.

        Returns ``None`` when no limits are configured (registry unavailable
        or no quota/budget limits).  Returns a :class:`QuotaReservationResult`
        when limits exist — ``reserved=True`` on success, ``reserved=False``
        on rejection or failure (fail-closed).
        """
        if self._quota_registry is None:
            return None

        settings = get_settings()
        provider = self._registry.get(provider_id)
        provider_config = provider.provider_config

        cost_est = estimate_request_cost(request, provider_config)

        if settings.ai_max_estimated_request_cost > 0:
            if not cost_est.cost_known:
                return QuotaReservationResult(
                    reserved=False,
                    reservation_id=reservation_id,
                    reason="cost_unknown",
                )
            if cost_est.estimated_cost > settings.ai_max_estimated_request_cost:
                return QuotaReservationResult(
                    reserved=False,
                    reservation_id=reservation_id,
                    reason="cost_exceeded",
                )

        quota_config: ProviderQuotaConfig | None = None
        try:
            quota_config = await self._quota_registry.get_provider_quota(provider_id)
        except Exception as exc:
            logger.warning(
                "Failed to load provider quota config",
                provider_id=provider_id,
                error=str(exc),
            )
        if (quota_config is None or not quota_config.limits) and isinstance(
            provider_config, ProviderConfig
        ):
            quota_config = build_quota_config_from_provider_config(provider_id, provider_config)
        if quota_config is None or not quota_config.limits:
            return None

        global_budget = await self._get_global_budget()

        limit = quota_config.limit_for(QuotaWindow.DAY) or quota_config.limits[0]

        reserve_req = QuotaReservationRequest(
            provider_id=provider_id,
            reservation_id=reservation_id,
            window=QuotaWindow.DAY,
            request_count=1,
            input_tokens=cost_est.input_tokens,
            output_tokens=cost_est.output_tokens,
            total_tokens=cost_est.total_tokens,
            estimated_cost=Decimal(str(cost_est.estimated_cost)),
            cost_known=cost_est.cost_known,
            limit=limit,
            daily_budget=global_budget.daily_budget,
            monthly_budget=global_budget.monthly_budget,
        )

        try:
            return await self._quota_registry.reserve_capacity(reserve_req)
        except Exception as exc:
            logger.warning(
                "Failed to reserve capacity",
                provider_id=provider_id,
                reservation_id=reservation_id,
                error=str(exc),
            )
            return QuotaReservationResult(
                reserved=False,
                reservation_id=reservation_id,
                reason="reserve_failed",
            )

    async def _settle_reservation(
        self,
        provider_id: str,
        request: AIRequest,
        response: AIResponse,
        reservation_id: str,
    ) -> None:
        """Settle a reservation with actual usage from a successful provider call."""
        if self._quota_registry is None:
            return
        try:
            config = self._get_provider_config(provider_id)
            input_cost = float(getattr(config, "input_cost_per_1k_tokens", 0.0) or 0.0)
            output_cost = float(getattr(config, "output_cost_per_1k_tokens", 0.0) or 0.0)
            actual_cost = (response.usage.prompt_tokens / 1000.0) * input_cost + (
                response.usage.completion_tokens / 1000.0
            ) * output_cost
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
                window=QuotaWindow.DAY,
            )
            result = await self._quota_registry.settle_reservation(
                reservation_id, usage, actual_cost=actual_cost
            )
            if not result.settled:
                logger.warning(
                    "Reservation settlement failed — capacity retained",
                    provider_id=provider_id,
                    reservation_id=reservation_id,
                    reason=result.reason,
                )
        except Exception as exc:
            logger.warning(
                "Failed to settle reservation",
                provider_id=provider_id,
                reservation_id=reservation_id,
                error=str(exc),
            )

    async def _handle_provider_failure(
        self,
        provider_id: str,
        reservation_id: str,
        exc: Exception,
    ) -> None:
        """Release a reservation on safe failures or retain it on indeterminate outcomes."""
        if self._quota_registry is None:
            return
        category = classify_failure(exc)
        safe_release_categories = frozenset(
            {
                FailureCategory.PROVIDER_UNAVAILABLE,
                FailureCategory.AUTHENTICATION_FAILURE,
                FailureCategory.CONFIGURATION_ERROR,
                FailureCategory.UNSUPPORTED_CAPABILITY,
                FailureCategory.INVALID_REQUEST,
                FailureCategory.RATE_LIMITED,
            }
        )
        if category in safe_release_categories:
            try:
                await self._quota_registry.release_reservation(reservation_id)
            except Exception as exc2:
                logger.warning(
                    "Failed to release reservation after safe failure",
                    provider_id=provider_id,
                    reservation_id=reservation_id,
                    error=str(exc2),
                )
        else:
            logger.warning(
                "Provider failure with indeterminate billing outcome; "
                "reservation retained for reconciliation",
                provider_id=provider_id,
                reservation_id=reservation_id,
                failure_category=category,
                error=str(exc),
            )

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
