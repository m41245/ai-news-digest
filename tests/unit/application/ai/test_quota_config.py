"""
Unit tests for M79 quota and budget configuration.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from ai_news_digest.core.config import Settings


@contextmanager
def _settings_with(**kwargs: object) -> Iterator[Settings]:
    """Construct Settings with alias'd fields via environment variables.

    pydantic-settings v2 ignores init-kwargs for fields that declare a
    ``validation_alias``.  We work around this by setting the matching
    environment variable, which pydantic-settings reads with highest
    precedence.
    """
    env_vars: dict[str, str] = {}
    for key, value in kwargs.items():
        field = Settings.model_fields.get(key)
        if field and field.validation_alias and isinstance(field.validation_alias, str):
            env_vars[field.validation_alias] = str(value)
        else:
            env_vars[key] = str(value)
    with patch.dict(os.environ, env_vars, clear=False):
        yield Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            jwt_secret_key="a" * 64,
        )


class TestQuotaBudgetSettings:
    """Tests for M79 quota and budget configuration."""

    def test_ai_daily_cost_budget_defaults_to_zero(self) -> None:
        with _settings_with() as settings:
            assert settings.ai_daily_cost_budget == 0.0

    def test_ai_monthly_cost_budget_defaults_to_zero(self) -> None:
        with _settings_with() as settings:
            assert settings.ai_monthly_cost_budget == 0.0

    def test_ai_max_estimated_request_cost_defaults_to_zero(self) -> None:
        with _settings_with() as settings:
            assert settings.ai_max_estimated_request_cost == 0.0

    def test_ai_daily_cost_budget_can_be_set(self) -> None:
        with _settings_with(ai_daily_cost_budget=10.0) as settings:
            assert settings.ai_daily_cost_budget == 10.0

    def test_ai_monthly_cost_budget_can_be_set(self) -> None:
        with _settings_with(ai_monthly_cost_budget=100.0) as settings:
            assert settings.ai_monthly_cost_budget == 100.0

    def test_ai_max_estimated_request_cost_can_be_set(self) -> None:
        with _settings_with(ai_max_estimated_request_cost=0.05) as settings:
            assert settings.ai_max_estimated_request_cost == 0.05

    def test_ai_daily_cost_budget_rejects_negative(self) -> None:
        env = {"AI_DAILY_COST_BUDGET": "-1.0"}
        with patch.dict(os.environ, env), pytest.raises(ValidationError):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                jwt_secret_key="a" * 64,
            )

    def test_ai_monthly_cost_budget_rejects_negative(self) -> None:
        env = {"AI_MONTHLY_COST_BUDGET": "-1.0"}
        with patch.dict(os.environ, env), pytest.raises(ValidationError):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                jwt_secret_key="a" * 64,
            )

    def test_ai_max_estimated_request_cost_rejects_negative(self) -> None:
        env = {"AI_MAX_ESTIMATED_REQUEST_COST": "-1.0"}
        with patch.dict(os.environ, env), pytest.raises(ValidationError):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                jwt_secret_key="a" * 64,
            )


class TestProviderQuotaSettings:
    """Tests for per-provider quota and pricing configuration."""

    def test_openai_request_limit_defaults_to_zero(self) -> None:
        with _settings_with() as settings:
            assert settings.openai_request_limit == 0

    def test_openai_token_limit_defaults_to_zero(self) -> None:
        with _settings_with() as settings:
            assert settings.openai_token_limit == 0

    def test_openai_cost_limit_defaults_to_zero(self) -> None:
        with _settings_with() as settings:
            assert settings.openai_cost_limit == 0.0

    def test_openai_pricing_defaults_to_zero(self) -> None:
        with _settings_with() as settings:
            assert settings.openai_input_cost_per_1k_tokens == 0.0
            assert settings.openai_output_cost_per_1k_tokens == 0.0

    def test_anthropic_quota_defaults_to_zero(self) -> None:
        with _settings_with() as settings:
            assert settings.anthropic_request_limit == 0
            assert settings.anthropic_token_limit == 0
            assert settings.anthropic_cost_limit == 0.0

    def test_gemini_quota_defaults_to_zero(self) -> None:
        with _settings_with() as settings:
            assert settings.gemini_request_limit == 0
            assert settings.gemini_token_limit == 0
            assert settings.gemini_cost_limit == 0.0

    def test_xai_quota_defaults_to_zero(self) -> None:
        with _settings_with() as settings:
            assert settings.xai_request_limit == 0
            assert settings.xai_token_limit == 0
            assert settings.xai_cost_limit == 0.0

    def test_quota_settings_reject_negative_values(self) -> None:
        env = {"OPENAI_REQUEST_LIMIT": "-1"}
        with patch.dict(os.environ, env), pytest.raises(ValidationError):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                jwt_secret_key="a" * 64,
            )

    def test_quota_settings_accept_positive_values(self) -> None:
        with _settings_with(
            openai_request_limit=100,
            openai_token_limit=10000,
            openai_cost_limit=5.0,
        ) as settings:
            assert settings.openai_request_limit == 100
            assert settings.openai_token_limit == 10000
            assert settings.openai_cost_limit == 5.0


__all__ = ["TestProviderQuotaSettings", "TestQuotaBudgetSettings"]
