from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from ai_news_digest.core.exceptions import ResourceNotFoundError

if TYPE_CHECKING:
    from ai_news_digest.domain.models.digest import Digest
    from ai_news_digest.domain.ports.digest_repository import DigestRepository


@dataclass(slots=True, frozen=True)
class UpdateDigestRequest:
    """
    Request DTO for updating an existing digest.
    """

    id: UUID
    title: str | None = None
    content: str | None = None
    article_ids: list[UUID] | None = None


class UpdateDigestUseCase:
    """
    Application use case responsible for updating an existing digest.
    """

    def __init__(
        self,
        repository: DigestRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        request: UpdateDigestRequest,
    ) -> Digest:
        """
        Update an existing digest and return the updated representation.
        """
        digest = await self._repository.get_by_id(request.id)

        if digest is None:
            raise ResourceNotFoundError(f"Digest {request.id} not found.")

        if request.title is not None:
            digest.title = request.title

        if request.content is not None:
            digest.content = request.content

        if request.article_ids is not None:
            digest.article_ids = request.article_ids

        updated = await self._repository.update(digest)

        return updated
