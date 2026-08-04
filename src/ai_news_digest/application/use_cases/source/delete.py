from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from ai_news_digest.application.exceptions.source import (
    SourceNotFoundError,
)

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.source_repository import SourceRepository


class DeleteSourceUseCase:
    """
    Application use case responsible for deleting an existing news source.
    """

    def __init__(
        self,
        repository: SourceRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        source_id: UUID,
    ) -> None:
        """
        Delete a news source.

        Raises:
            SourceNotFoundError: If the source does not exist.
        """

        source = await self._repository.get_by_id(source_id)

        if source is None:
            raise SourceNotFoundError(str(source_id))

        await self._repository.delete(source_id)
