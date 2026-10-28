from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class SourceDecisionRequest:
    id: UUID
    reason: str = ""
    decision: str | None = None
    actor_user_id: UUID | str | None = None
    user_id: UUID | str | None = None


ApproveSourceRequest = SourceDecisionRequest
RejectSourceRequest = SourceDecisionRequest
DeactivateSourceRequest = SourceDecisionRequest
DecideSourceRequest = SourceDecisionRequest
