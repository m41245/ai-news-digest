from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.models.source_trust_decision import SourceTrustDecision
from ai_news_digest.domain.ports.source_trust_decision_repository import (
    SourceTrustDecisionRepository as SourceTrustDecisionRepositoryPort,
)
from ai_news_digest.infrastructure.database.models.source_trust_decision_model import (
    SourceTrustDecisionModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class SourceTrustDecisionRepository(
    BaseRepository[SourceTrustDecisionModel],
    SourceTrustDecisionRepositoryPort,
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, decision: SourceTrustDecision) -> SourceTrustDecision:
        model = SourceTrustDecisionModel(
            id=str(decision.id),
            source_id=str(decision.source_id),
            actor_user_id=str(decision.actor_user_id),
            decision=decision.decision,
            previous_status=decision.previous_status,
            resulting_status=decision.resulting_status,
            previous_is_active=decision.previous_is_active,
            resulting_is_active=decision.resulting_is_active,
            reason=decision.reason,
            validation_outcome=decision.validation_outcome,
            created_at=decision.created_at,
        )
        self._session.add(model)
        await self._flush()
        await self._refresh(model)
        return SourceTrustDecision(
            id=UUID(model.id),
            source_id=UUID(model.source_id),
            actor_user_id=UUID(model.actor_user_id),
            decision=model.decision,
            previous_status=model.previous_status,
            resulting_status=model.resulting_status,
            previous_is_active=model.previous_is_active,
            resulting_is_active=model.resulting_is_active,
            reason=model.reason,
            validation_outcome=model.validation_outcome,
            created_at=model.created_at,
        )

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        await self._session.rollback()

    async def list_for_source(
        self,
        source_id: UUID,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SourceTrustDecision]:
        statement = (
            select(SourceTrustDecisionModel)
            .where(SourceTrustDecisionModel.source_id == str(source_id))
            .order_by(SourceTrustDecisionModel.created_at.desc())
        )
        if limit is not None:
            statement = statement.limit(limit).offset(offset)
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [
            SourceTrustDecision(
                id=UUID(m.id),
                source_id=UUID(m.source_id),
                actor_user_id=UUID(m.actor_user_id),
                decision=m.decision,
                previous_status=m.previous_status,
                resulting_status=m.resulting_status,
                previous_is_active=m.previous_is_active,
                resulting_is_active=m.resulting_is_active,
                reason=m.reason,
                validation_outcome=m.validation_outcome,
                created_at=m.created_at,
            )
            for m in models
        ]

    async def count_for_source(self, source_id: UUID) -> int:
        statement = (
            select(func.count())
            .select_from(SourceTrustDecisionModel)
            .where(SourceTrustDecisionModel.source_id == str(source_id))
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())
