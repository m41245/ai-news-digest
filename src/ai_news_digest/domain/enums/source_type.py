from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    """
    Classification of news sources by role/type.
    """

    OFFICIAL_COMPANY = "official_company"

    TECH_PUBLICATION = "tech_publication"

    BUSINESS_NEWS = "business_news"

    RESEARCH_ORG = "research_org"

    OTHER = "other"
