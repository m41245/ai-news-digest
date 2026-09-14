from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from ai_news_digest.domain.models.claim import Claim
from ai_news_digest.domain.models.evidence import Evidence
from ai_news_digest.domain.ports.claim_repository import ClaimRepository
from ai_news_digest.infrastructure.database.mappers.claim_mapper import ClaimMapper
from ai_news_digest.infrastructure.database.mappers.evidence_mapper import EvidenceMapper
from ai_news_digest.infrastructure.database.models.claim_evidence_model import (
    ClaimEvidenceModel,
)
from ai_news_digest.infrastructure.database.models.claim_model import ClaimModel
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class SqlAlchemyClaimRepository(BaseRepository[ClaimModel], ClaimRepository):
    """
    SQLAlchemy implementation of the ClaimRepository port.
    """

    def __init__(self, session: Any) -> None:
        super().__init__(session)

    async def create_claim(self, claim: Claim) -> Claim:
        model = ClaimMapper.to_model(claim)
        model = await self._add_and_refresh(model)
        return ClaimMapper.to_domain(model)

    async def get_by_id(self, claim_id: UUID) -> Claim | None:
        statement = (
            select(ClaimModel)
            .options(selectinload(ClaimModel.evidence_items))
            .where(ClaimModel.id == str(claim_id))
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return ClaimMapper.to_domain(model)

    async def list_by_article_id(self, article_id: UUID) -> list[Claim]:
        statement = (
            select(ClaimModel)
            .options(selectinload(ClaimModel.evidence_items))
            .where(ClaimModel.article_id == str(article_id))
            .order_by(ClaimModel.created_at.asc())
        )
        result = await self._session.execute(statement)
        return [ClaimMapper.to_domain(model) for model in result.scalars().all()]

    async def update_claim(self, claim: Claim) -> Claim:
        statement = select(ClaimModel).where(ClaimModel.id == str(claim.id))
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Claim with id '{claim.id}' was not found.")
        ClaimMapper.update_model(model, claim)
        await self._commit()
        model = await self._refresh(model)
        return ClaimMapper.to_domain(model)

    async def delete_claims_for_article(self, article_id: UUID) -> int:
        stmt = delete(ClaimModel).where(ClaimModel.article_id == str(article_id))
        result = await self._session.execute(stmt)
        await self._commit()
        return int(result.rowcount)

    async def create_evidence(self, evidence: Evidence) -> Evidence:
        model = EvidenceMapper.to_model(evidence)
        model = await self._add_and_refresh(model)
        return EvidenceMapper.to_domain(model)

    async def list_evidence_by_claim_id(self, claim_id: UUID) -> list[Evidence]:
        statement = (
            select(ClaimEvidenceModel)
            .where(ClaimEvidenceModel.claim_id == str(claim_id))
            .order_by(ClaimEvidenceModel.created_at.asc())
        )
        result = await self._session.execute(statement)
        return [EvidenceMapper.to_domain(model) for model in result.scalars().all()]

    async def delete_evidence_for_claim(self, claim_id: UUID) -> int:
        stmt = delete(ClaimEvidenceModel).where(
            ClaimEvidenceModel.claim_id == str(claim_id)
        )
        result = await self._session.execute(stmt)
        await self._commit()
        return int(result.rowcount)


__all__ = ["SqlAlchemyClaimRepository"]
