from __future__ import annotations

from enum import StrEnum


class TrendType(StrEnum):
    TOPIC_TREND = "topic_trend"
    COMPANY_TREND = "company_trend"
    CATEGORY_TREND = "category_trend"
    STORY_TREND = "story_trend"
    EMERGING_TREND = "emerging_trend"


__all__ = ["TrendType"]
