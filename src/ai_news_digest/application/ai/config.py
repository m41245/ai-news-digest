from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProviderConfig:
    """
    Configuration shared by every AI provider.
    """

    provider_name: str

    api_key: str | None

    enabled: bool = True

    priority: int = 50

    base_url: str | None = None

    model: str | None = None

    timeout: float = 60.0

    max_retries: int = 3

    free_tier: bool = False

    quality_score: float = 0.0

    speed_score: float = 0.0

    reliability_score: float = 0.0

    context_window: int = 0