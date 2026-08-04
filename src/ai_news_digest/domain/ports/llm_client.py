from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_news_digest.domain.models.article import Article


class LLMClient(ABC):
    """
    Large Language Model interface.
    """

    @abstractmethod
    async def summarize(
        self,
        article: Article,
    ) -> str:
        """
        Generate a concise summary for an article.
        """
        raise NotImplementedError

    @abstractmethod
    async def categorize(
        self,
        article: Article,
    ) -> str:
        """
        Predict a category for an article.
        """
        raise NotImplementedError
