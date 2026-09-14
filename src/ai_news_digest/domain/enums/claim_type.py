from __future__ import annotations

from enum import StrEnum


class ClaimType(StrEnum):
    """Classification of an AI-extracted claim."""

    FACT = "fact"
    EVENT = "event"
    QUANTITATIVE = "quantitative"
    PRODUCT = "product"
    COMPANY = "company"
    RESEARCH = "research"
    ANNOUNCEMENT = "announcement"
    BUSINESS = "business"
    POLICY = "policy"
    OTHER = "other"
