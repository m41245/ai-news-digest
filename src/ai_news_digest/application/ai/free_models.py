"""Explicit production allowlist for the free-only AI policy.

Allowlisting does not guarantee provider access or free-tier eligibility for
every project; confirm current availability and account limits with the provider.
"""

from __future__ import annotations

import os

from ai_news_digest.core.config import get_settings

GEMINI_FREE_MODEL_IDS: frozenset[str] = frozenset(
    {
        "gemini-3.8-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    }
)

GROQ_FREE_MODEL_IDS: frozenset[str] = frozenset(
    {
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
    }
)

FREE_PROVIDER_MODEL_ALLOWLIST: dict[str, frozenset[str]] = {
    "gemini": GEMINI_FREE_MODEL_IDS,
    "groq": GROQ_FREE_MODEL_IDS,
}

# Common aliases for compatibility with callers/tests.
ALLOWED_FREE_MODELS = FREE_PROVIDER_MODEL_ALLOWLIST
FREE_MODEL_ALLOWLIST = FREE_PROVIDER_MODEL_ALLOWLIST
GEMINI_ALLOWED_MODELS = GEMINI_FREE_MODEL_IDS
GROQ_ALLOWED_MODELS = GROQ_FREE_MODEL_IDS


def is_free_provider(provider_id: str) -> bool:
    """Return True only when *provider_id* is explicitly allowlisted as free."""
    return provider_id in FREE_PROVIDER_MODEL_ALLOWLIST


def is_allowlisted_free_model(provider_id: str, model: str | None) -> bool:
    """Return True only for explicitly allowlisted free provider/model pairs.

    Providers or models that are not present in ``FREE_PROVIDER_MODEL_ALLOWLIST``
    are never considered free, even if a ``free_tier`` flag is set elsewhere.
    """
    allowed = FREE_PROVIDER_MODEL_ALLOWLIST.get(provider_id)
    if allowed is None:
        return False
    return model is not None and model in allowed


def _settings_free_only(settings: object) -> bool:
    for attr in ("ai_free_only", "free_only", "free_only_mode", "v1_free_only"):
        value = getattr(settings, attr, False)
        if isinstance(value, bool) and value:
            return True
        if isinstance(value, str) and value.strip().lower() in {"1", "true", "yes", "on"}:
            return True
        if isinstance(value, int) and not isinstance(value, bool) and value != 0:
            return True
    environment = getattr(settings, "environment", None)
    return isinstance(environment, str) and environment.strip().lower() == "production"


def is_free_only_mode(settings: object | None = None) -> bool:
    """Determine whether the V1 free-only policy is active.

    Free-only mode is opt-in via explicit settings/flags. It is also enabled
    for production by default. Other environments keep existing provider
    functionality unless an explicit flag is set.
    """
    if settings is None:
        settings = get_settings()
    if settings is not None and _settings_free_only(settings):
        return True
    for env_name in ("AI_FREE_ONLY", "FREE_ONLY", "FREE_ONLY_MODE", "V1_FREE_ONLY"):
        value = os.getenv(env_name, "").strip().lower()
        if value in {"1", "true", "yes", "on"}:
            return True
    return False


__all__ = [
    "ALLOWED_FREE_MODELS",
    "FREE_MODEL_ALLOWLIST",
    "FREE_PROVIDER_MODEL_ALLOWLIST",
    "GEMINI_ALLOWED_MODELS",
    "GEMINI_FREE_MODEL_IDS",
    "GROQ_ALLOWED_MODELS",
    "GROQ_FREE_MODEL_IDS",
    "is_allowlisted_free_model",
    "is_free_only_mode",
    "is_free_provider",
]
