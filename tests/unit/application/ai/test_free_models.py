"""Tests for the explicit free-model policy."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ai_news_digest.application.ai.free_models import (
    FREE_PROVIDER_MODEL_ALLOWLIST,
    is_allowlisted_free_model,
    is_free_only_mode,
    resolve_free_only,
)
from ai_news_digest.core.config import Settings


@pytest.mark.parametrize(
    ("provider_id", "model_name"),
    [
        ("gemini", "gemini-2.5-flash"),
        ("groq", "openai/gpt-oss-20b"),
    ],
)
def test_allowlisted_free_provider_models_are_accepted(
    provider_id: str,
    model_name: str,
) -> None:
    assert model_name in FREE_PROVIDER_MODEL_ALLOWLIST[provider_id]
    assert is_allowlisted_free_model(provider_id, model_name)


@pytest.mark.parametrize(
    ("provider_id", "model_name"),
    [
        ("openai", "gpt-4o"),
        ("anthropic", "claude-3-5-sonnet"),
        ("gemini", "gemini-paid-model"),
        ("groq", "non-allowlisted-model"),
        ("groq", "openai/gpt-oss-safeguard-20b"),
        ("groq", "qwen/qwen3.8-27b"),
    ],
)
def test_non_allowlisted_provider_models_are_rejected(
    provider_id: str,
    model_name: str,
) -> None:
    assert not is_allowlisted_free_model(provider_id, model_name)


def test_free_only_mode_uses_settings_flag() -> None:
    assert is_free_only_mode(Settings(ai_free_only=True))
    assert not is_free_only_mode(Settings(ai_free_only=False, environment="testing"))


def test_production_settings_always_enable_free_only_mode() -> None:
    settings = SimpleNamespace(ai_free_only=False, environment="production")
    assert is_free_only_mode(settings)


def test_resolve_free_only_defaults_to_configured_mode() -> None:
    assert resolve_free_only(None, settings=Settings(ai_free_only=True, environment="testing"))
    assert not resolve_free_only(None, settings=Settings(ai_free_only=False, environment="testing"))


def test_resolve_free_only_production_enforced() -> None:
    assert resolve_free_only(
        False, settings=SimpleNamespace(ai_free_only=False, environment="production")
    )
    assert resolve_free_only(
        True, settings=SimpleNamespace(ai_free_only=False, environment="production")
    )


def test_resolve_free_only_explicit_override_allowed_in_nonproduction() -> None:
    assert not resolve_free_only(False, settings=Settings(ai_free_only=True, environment="testing"))
    assert resolve_free_only(True, settings=Settings(ai_free_only=False, environment="testing"))
