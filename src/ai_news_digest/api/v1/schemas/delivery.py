"""
Digest delivery API schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class DeliveryResponse(BaseModel):
    """Response model representing a digest delivery record."""

    id: UUID
    digest_id: UUID
    recipient: str
    status: str
    attempt_count: int
    sent_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: Annotated[str | None, Field(default=None)] = None
    provider_message_id: str | None = None
    created_at: datetime | None = None


__all__ = ["DeliveryResponse"]
