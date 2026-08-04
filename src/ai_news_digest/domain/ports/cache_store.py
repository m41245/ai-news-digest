from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CacheStore(ABC):
    """
    Generic cache interface.
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        Retrieve a value from cache.
        """
        raise NotImplementedError

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """
        Store a value in cache.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Remove a value from cache.
        """
        raise NotImplementedError

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check whether a cache key exists.
        """
        raise NotImplementedError
