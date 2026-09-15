from __future__ import annotations

from enum import StrEnum


class TrendStatus(StrEnum):
    EMERGING = "emerging"
    RISING = "rising"
    SUSTAINED = "sustained"
    COOLING = "cooling"
    STALE = "stale"


__all__ = ["TrendStatus"]
