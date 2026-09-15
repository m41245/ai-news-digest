from __future__ import annotations

from enum import StrEnum


class StoryEventType(StrEnum):
    ANNOUNCEMENT = "announcement"
    PRODUCT_LAUNCH = "product_launch"
    PARTNERSHIP = "partnership"
    FUNDING = "funding"
    ACQUISITION = "acquisition"
    RESEARCH_RELEASE = "research_release"
    MODEL_RELEASE = "model_release"
    POLICY_OR_REGULATION = "policy_or_regulation"
    LEGAL_DEVELOPMENT = "legal_development"
    INCIDENT = "incident"
    SECURITY_EVENT = "security_event"
    COMPANY_RESPONSE = "company_response"
    RESEARCH_FINDING = "research_finding"
    PERFORMANCE_DEVELOPMENT = "performance_development"
    MARKET_DEVELOPMENT = "market_development"
    OTHER = "other"


__all__ = ["StoryEventType"]
