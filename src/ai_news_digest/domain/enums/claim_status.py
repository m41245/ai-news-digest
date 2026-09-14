from __future__ import annotations

from enum import StrEnum


class ClaimStatus(StrEnum):
    """Evidence-backed status of a claim."""

    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    UNVERIFIED = "unverified"
