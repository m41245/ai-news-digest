from __future__ import annotations

from dataclasses import dataclass

from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.application.ai.models import AIRequest


@dataclass(slots=True)
class CostEstimate:
    """Bounded cost estimate for an AI request."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    cost_known: bool = False
    pricing_known: bool = False
    note: str = ""


def estimate_request_cost(
    request: AIRequest,
    provider_config: ProviderConfig | None,
) -> CostEstimate:
    """Return a bounded cost estimate for the given request and provider.

    Uses configured provider pricing when available. If pricing is unknown,
    returns an estimate with cost_known=False and a conservative note.
    """
    input_tokens = _estimate_input_tokens(request)
    output_tokens = max(0, request.max_tokens)

    total_tokens = input_tokens + output_tokens
    estimated_cost: float = 0.0
    cost_known: bool = False
    pricing_known: bool = False
    note: str = ""

    if provider_config is not None:
        input_cost = provider_config.input_cost_per_1k_tokens
        output_cost = provider_config.output_cost_per_1k_tokens

        if (
            input_cost is not None
            and output_cost is not None
            and (input_cost > 0 or output_cost > 0)
        ):
            pricing_known = True
            input_cost_val = float(input_cost)
            output_cost_val = float(output_cost)
            estimated_cost = (input_tokens / 1000.0) * input_cost_val + (
                output_tokens / 1000.0
            ) * output_cost_val
            cost_known = True
            note = "cost estimated from configured pricing"
        else:
            note = "pricing unknown; cost estimate unavailable"
    else:
        note = "no provider config; cost estimate unavailable"

    return CostEstimate(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
        cost_known=cost_known,
        pricing_known=pricing_known,
        note=note,
    )


def _estimate_input_tokens(request: AIRequest) -> int:
    """Bounded conservative input token estimate.

    Uses a simple character-based heuristic (~4 chars per token) capped
    at a reasonable maximum to avoid unbounded estimation.
    """
    system_text = request.system_prompt or ""
    user_text = request.user_prompt or ""
    combined = system_text + user_text
    if not combined:
        return 0
    estimated = max(1, len(combined) // 4)
    return min(estimated, 100000)


def estimate_tokens_from_chars(char_count: int) -> int:
    """Public helper for bounded token estimation from character count."""
    if char_count <= 0:
        return 0
    return min(char_count // 4, 100000)


__all__ = [
    "CostEstimate",
    "estimate_request_cost",
    "estimate_tokens_from_chars",
]
