from __future__ import annotations

from typing import TYPE_CHECKING

from ai_news_digest.application.dto.source import (
    SourceResponse,
    UpdateSourceRequest,
)
from ai_news_digest.application.exceptions.source import (
    SourceNotFoundError,
)
from ai_news_digest.domain.enums.source_status import SourceStatus

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.source_repository import SourceRepository


class UpdateSourceUseCase:
    """
    Application use case responsible for updating an existing news source.
    """

    def __init__(
        self,
        repository: SourceRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        request: UpdateSourceRequest,
    ) -> SourceResponse:
        """
        Update an existing news source and return the updated representation.
        """

        source = await self._repository.get_by_id(request.id)

        if source is None:
            raise SourceNotFoundError(str(request.id))

        status = (
            SourceStatus(request.status)
            if request.status is not None
            else None
        )

        source.update(
            name=request.name,
            feed_url=request.feed_url,
            website_url=request.website_url,
            description=request.description,
            is_active=request.is_active,
            status=status,
        )

        updated = await self._repository.update(source)

        return SourceResponse(
            id=str(updated.id),
            name=updated.name,
            feed_url=updated.feed_url,
            website_url=updated.website_url,
            description=updated.description,
            is_active=updated.is_active,
            status=updated.status.value,
        )
