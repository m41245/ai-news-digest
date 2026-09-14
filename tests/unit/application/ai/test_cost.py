"""
Unit tests for M79 cost estimation.
"""

from __future__ import annotations

from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.application.ai.cost import (
    CostEstimate,
    estimate_request_cost,
    estimate_tokens_from_chars,
)
from ai_news_digest.application.ai.models import AIRequest


class TestEstimateTokensFromChars:
    """Tests for bounded token estimation from character count."""

    def test_zero_chars_returns_zero(self) -> None:
        assert estimate_tokens_from_chars(0) == 0

    def test_negative_chars_returns_zero(self) -> None:
        assert estimate_tokens_from_chars(-100) == 0

    def test_reasonable_char_count(self) -> None:
        assert estimate_tokens_from_chars(4000) == 1000

    def test_caps_at_maximum(self) -> None:
        assert estimate_tokens_from_chars(1000000) == 100000


class TestEstimateRequestCost:
    """Tests for request cost estimation."""

    def _make_request(
        self,
        system: str = "s",
        user: str = "u",
        max_tokens: int = 1024,
    ) -> AIRequest:
        return AIRequest(
            system_prompt=system,
            user_prompt=user,
            max_tokens=max_tokens,
        )

    def test_none_config_returns_unknown_cost(self) -> None:
        request = self._make_request()
        estimate = estimate_request_cost(request, None)
        assert estimate.cost_known is False
        assert estimate.pricing_known is False
        assert estimate.estimated_cost == 0.0

    def test_zero_pricing_returns_unknown_cost(self) -> None:
        request = self._make_request()
        config = ProviderConfig(
            provider_name="openai",
            api_key="test",
            input_cost_per_1k_tokens=0.0,
            output_cost_per_1k_tokens=0.0,
        )
        estimate = estimate_request_cost(request, config)
        assert estimate.cost_known is False
        assert estimate.pricing_known is False

    def test_known_pricing_returns_known_cost(self) -> None:
        request = AIRequest(
            system_prompt="system " * 100,
            user_prompt="user " * 100,
            max_tokens=512,
        )
        config = ProviderConfig(
            provider_name="openai",
            api_key="test",
            input_cost_per_1k_tokens=0.01,
            output_cost_per_1k_tokens=0.02,
        )
        estimate = estimate_request_cost(request, config)
        assert estimate.cost_known is True
        assert estimate.pricing_known is True
        assert estimate.estimated_cost > 0.0
        assert estimate.input_tokens > 0
        assert estimate.output_tokens == 512

    def test_empty_prompts_return_zero_tokens(self) -> None:
        request = AIRequest(
            system_prompt="",
            user_prompt="",
            max_tokens=0,
        )
        config = ProviderConfig(
            provider_name="openai",
            api_key="test",
            input_cost_per_1k_tokens=0.01,
            output_cost_per_1k_tokens=0.02,
        )
        estimate = estimate_request_cost(request, config)
        assert estimate.input_tokens >= 0
        assert estimate.output_tokens == 0

    def test_cost_estimate_is_bounded(self) -> None:
        huge_prompt = "a" * 1000000
        request = AIRequest(
            system_prompt=huge_prompt,
            user_prompt=huge_prompt,
            max_tokens=4096,
        )
        config = ProviderConfig(
            provider_name="openai",
            api_key="test",
            input_cost_per_1k_tokens=0.01,
            output_cost_per_1k_tokens=0.02,
        )
        estimate = estimate_request_cost(request, config)
        assert estimate.input_tokens <= 100000
        assert estimate.output_tokens == 4096


class TestCostEstimateDataclass:
    """Tests for the CostEstimate dataclass."""

    def test_default_values(self) -> None:
        estimate = CostEstimate()
        assert estimate.input_tokens == 0
        assert estimate.output_tokens == 0
        assert estimate.total_tokens == 0
        assert estimate.estimated_cost == 0.0
        assert estimate.cost_known is False
        assert estimate.pricing_known is False


__all__ = [
    "TestCostEstimateDataclass",
    "TestEstimateRequestCost",
    "TestEstimateTokensFromChars",
]
