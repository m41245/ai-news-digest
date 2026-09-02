from __future__ import annotations

from enum import StrEnum


class DeliveryStatus(StrEnum):
    """
    Processing lifecycle of a digest delivery.
    """

    PENDING = "pending"

    SENT = "sent"

    FAILED = "failed"


__all__ = ["DeliveryStatus"]
