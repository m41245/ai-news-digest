from __future__ import annotations

from enum import StrEnum


class ConflictType(StrEnum):
    """Classification of a detected conflict between claims."""

    NUMERIC = "numeric"
    DATE = "date"
    EVENT_STATUS = "event_status"
    PRODUCT_ATTRIBUTE = "product_attribute"
    COMPANY_STATEMENT = "company_statement"
    AVAILABILITY = "availability"
    ANNOUNCEMENT = "announcement"
    QUANTITY = "quantity"
    OTHER = "other"


__all__ = ["ConflictType"]
