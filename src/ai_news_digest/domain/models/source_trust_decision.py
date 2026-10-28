from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class SourceTrustDecision:
    """Durable record of an administrator's source trust decision."""

    id: UUID = field(default_factory=uuid4)
    source_id: UUID = field(default_factory=uuid4)
    actor_user_id: UUID = field(default_factory=uuid4)
    decision: str = ""
    previous_status: str = ""
    resulting_status: str = ""
    previous_is_active: bool = False
    resulting_is_active: bool = False
    reason: str = ""
    validation_outcome: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
