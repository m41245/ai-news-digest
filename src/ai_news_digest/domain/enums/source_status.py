from __future__ import annotations

from enum import StrEnum


class SourceStatus(StrEnum):
    """
    Processing status of a news source.
    """

    PENDING_REVIEW = "pending_review"

    VERIFIED = "verified"

    REJECTED = "rejected"

    INACTIVE = "inactive"
