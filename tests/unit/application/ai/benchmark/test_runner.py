"""
Unit tests for M80 benchmark runner.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_news_digest.application.ai.benchmark.models import (
    BenchmarkRun,
)
from ai_news_digest.application.ai.benchmark.runner import (
    BenchmarkExecutionConfig,
    BenchmarkRunner,
)
from ai_news_digest.application.ai.provider_manager import ProviderManager
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.application.ai.providers.base import AIProvider
from ai_news_digest.core.config import Settings


@pytest.fixture
def mock_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    provider = MagicMock(spec=AIProvider)
    provider.id = "test-provider"
    provider.name = "Test Provider"
    provider.enabled = True
    provider.priority = MagicMock(return_value=10)
    provider.capabilities = {"summarization"}
    provider.provider_name = "test_provider"
    provider.model_name = "test-model"
    provider.available = AsyncMock(return_value=True)
    provider.generate = AsyncMock()
    registry.register(provider)
    return registry


@pytest.fixture
def mock_provider_manager(mock_registry: ProviderRegistry) -> MagicMock:
    pm = MagicMock(spec=ProviderManager)
    pm.generate = AsyncMock()
    return pm


@pytest.fixture
def runner(mock_provider_manager: MagicMock, mock_registry: ProviderRegistry) -> BenchmarkRunner:
    config = BenchmarkExecutionConfig(
        provider_ids=("test-provider",),
        max_providers=1,
        max_cases=2,
        max_tasks=2,
        max_total_requests=2,
    )
    return BenchmarkRunner(
        provider_manager=mock_provider_manager,
        registry=mock_registry,
        config=config,
    )


class TestBenchmarkExecutionConfig:
    def test_valid_config(self):
        config = BenchmarkExecutionConfig()
        assert config.max_providers == 4
        assert config.max_cases == 10

    def test_max_providers_below_one_raises(self):
        with pytest.raises(ValueError):
            BenchmarkExecutionConfig(max_providers=0)

    def test_max_cases_below_one_raises(self):
        with pytest.raises(ValueError):
            BenchmarkExecutionConfig(max_cases=0)

    def test_timeout_below_one_raises(self):
        with pytest.raises(ValueError):
            BenchmarkExecutionConfig(timeout_seconds=0)


class TestBenchmarkRunnerAIEnabledFalse:
    @pytest.mark.asyncio
    async def test_ai_enabled_false_skips_execution(self, mock_registry: ProviderRegistry):
        from ai_news_digest.application.ai.benchmark.runner import BenchmarkRunner

        pm = MagicMock(spec=ProviderManager)
        config = BenchmarkExecutionConfig()
        runner = BenchmarkRunner(provider_manager=pm, registry=mock_registry, config=config)
        from unittest.mock import patch

        with patch("ai_news_digest.application.ai.benchmark.runner.get_settings") as mock_settings:
            mock_settings.return_value = Settings(ai_enabled=False)
            run = await runner.run()
            assert run.total_requests == 1
            assert run.failures == 1
            assert run.results[0].failure is not None
            assert "disabled" in run.results[0].failure.error_message.lower()


class TestBenchmarkRunnerExecution:
    @pytest.mark.asyncio
    async def test_run_returns_benchmark_run(self, runner: BenchmarkRunner):
        from unittest.mock import patch

        with patch("ai_news_digest.application.ai.benchmark.runner.get_settings") as mock_settings:
            mock_settings.return_value = Settings(ai_enabled=True)
            pm = runner._provider_manager
            from ai_news_digest.application.ai.models import AIResponse, AIUsage

            pm.generate.return_value = AIResponse(
                provider="test-provider",
                model="test-model",
                content=(
                    '{"summary": "A summary.", "categories": ["ai_research"], '
                    '"companies": [], "topics": [], "key_takeaways": [], '
                    '"why_it_matters": null}'
                ),
                usage=AIUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                latency_ms=100.0,
                estimated_cost=0.001,
                cost_known=True,
            )
            run = await runner.run()
            assert isinstance(run, BenchmarkRun)
            assert run.total_requests >= 0

    @pytest.mark.asyncio
    async def test_bounded_execution(self, mock_registry: ProviderRegistry):
        from unittest.mock import patch

        pm = MagicMock(spec=ProviderManager)
        pm.generate = AsyncMock()
        config = BenchmarkExecutionConfig(
            max_total_requests=2,
            max_providers=10,
        )
        runner = BenchmarkRunner(provider_manager=pm, registry=mock_registry, config=config)
        with patch("ai_news_digest.application.ai.benchmark.runner.get_settings") as mock_settings:
            mock_settings.return_value = Settings(ai_enabled=True)
            run = await runner.run()
            assert run.total_requests <= 2
