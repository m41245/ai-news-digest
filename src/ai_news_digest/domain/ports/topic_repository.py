from __future__ import annotations

from typing import Any


class TopicRepository:
    """
    Repository interface for topic entities.
    """

    async def get_by_id(self, topic_id: str) -> Any | None:
        raise NotImplementedError

    async def get_by_slug(self, slug: str) -> Any | None:
        raise NotImplementedError

    async def list_by_ids(self, topic_ids: list[str]) -> list[Any]:
        raise NotImplementedError

    async def create(self, topic: Any) -> Any:
        raise NotImplementedError

    async def update(self, topic: Any) -> Any:
        raise NotImplementedError

    async def delete(self, topic_id: str) -> None:
        raise NotImplementedError
