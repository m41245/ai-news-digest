from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ExtractArticleUseCase:
    """
    Minimal stub implementation for M45 final closure testing.
    """

    def __init__(
        self,
        article_fetcher: Any,
        html_extractor: Any,
        content_cleaner: Any,
        article_repository: Any,
    ) -> None:
        self.article_fetcher = article_fetcher
        self.html_extractor = html_extractor
        self.content_cleaner = content_cleaner
        self.article_repository = article_repository
