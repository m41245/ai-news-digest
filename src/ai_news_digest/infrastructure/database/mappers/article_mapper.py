from __future__ import annotations

import json
from uuid import UUID

from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.extraction_method import ExtractionMethod
from ai_news_digest.domain.enums.extraction_quality import ExtractionQuality
from ai_news_digest.domain.models.article import Article
from ai_news_digest.infrastructure.database.models.article_model import (
    ArticleModel,
)


class ArticleMapper:
    """
    Maps between Article domain objects and ArticleModel ORM entities.
    """

    @staticmethod
    def to_model(article: Article) -> ArticleModel:
        """Convert a domain Article into a new ORM ArticleModel."""
        return ArticleModel(
            id=str(article.id),
            source_id=str(article.source_id),
            category_id=(str(article.category_id) if article.category_id is not None else None),
            title=article.title,
            url=article.url,
            summary=article.summary,
            content=article.content,
            status=article.status,
            published_at=article.published_at,
            fetched_at=article.fetched_at,
            extraction_method=article.extraction_method,
            extraction_quality=article.extraction_quality,
            extracted_at=article.extracted_at,
            content_char_count=article.content_char_count,
            importance_score=article.importance_score,
            confidence=article.confidence,
            ai_provider=article.ai_provider,
            ai_model=article.ai_model,
            ai_processed_at=article.ai_processed_at,
            key_takeaways_json=_dump_list(article.key_takeaways),
            why_it_matters=article.why_it_matters,
            topics_json=_dump_list(article.topics),
            cluster_id=(str(article.cluster_id) if article.cluster_id is not None else None),
        )

    @staticmethod
    def update_model(
        model: ArticleModel,
        article: Article,
    ) -> None:
        """Update an existing ORM model from a domain Article."""
        model.source_id = str(article.source_id)
        model.category_id = str(article.category_id) if article.category_id is not None else None
        model.title = article.title
        model.url = article.url
        model.summary = article.summary
        model.content = article.content
        model.status = article.status
        model.published_at = article.published_at
        model.fetched_at = article.fetched_at
        model.extraction_method = article.extraction_method
        model.extraction_quality = article.extraction_quality
        model.extracted_at = article.extracted_at
        model.content_char_count = article.content_char_count
        model.importance_score = article.importance_score
        model.confidence = article.confidence
        model.ai_provider = article.ai_provider
        model.ai_model = article.ai_model
        model.ai_processed_at = article.ai_processed_at
        model.key_takeaways_json = _dump_list(article.key_takeaways)
        model.why_it_matters = article.why_it_matters
        model.topics_json = _dump_list(article.topics)
        model.cluster_id = str(article.cluster_id) if article.cluster_id is not None else None

    @staticmethod
    def to_domain(model: ArticleModel) -> Article:
        """Convert an ORM ArticleModel into a domain Article."""
        try:
            status = (
                ArticleStatus(model.status)
                if model.status is not None
                else ArticleStatus.NEW
            )
        except ValueError:
            status = ArticleStatus.NEW

        try:
            extraction_method = ExtractionMethod(
                model.extraction_method or ExtractionMethod.RSS.value,
            )
        except ValueError:
            extraction_method = ExtractionMethod.RSS

        try:
            extraction_quality = ExtractionQuality(
                model.extraction_quality or ExtractionQuality.NONE.value,
            )
        except ValueError:
            extraction_quality = ExtractionQuality.NONE

        return Article(
            id=UUID(model.id),
            source_id=UUID(model.source_id),
            category_id=(UUID(model.category_id) if model.category_id is not None else None),
            title=model.title,
            url=model.url,
            summary=model.summary,
            content=model.content,
            status=status,
            published_at=model.published_at,
            fetched_at=model.fetched_at,
            extraction_method=extraction_method,
            extraction_quality=extraction_quality,
            extracted_at=model.extracted_at,
            content_char_count=model.content_char_count,
            importance_score=model.importance_score,
            confidence=model.confidence,
            ai_provider=model.ai_provider,
            ai_model=model.ai_model,
            ai_processed_at=model.ai_processed_at,
            key_takeaways=_load_list(model.key_takeaways_json),
            why_it_matters=model.why_it_matters,
            topics=_load_list(model.topics_json),
            companies=tuple(
                link.company.name
                for link in (model.company_links or [])
                if link.company is not None
            ),
            categories=tuple(
                link.category.name
                for link in (model.category_links or [])
                if link.category is not None
            ),
            topic_ids=tuple(
                UUID(link.topic_id)
                for link in (model.topic_links or [])
            ),
            company_ids=tuple(
                UUID(link.company_id)
                for link in (model.company_links or [])
            ),
            category_ids=tuple(
                UUID(link.category_id)
                for link in (model.category_links or [])
            ),
            cluster_id=(UUID(model.cluster_id) if model.cluster_id is not None else None),
        )


def _dump_list(values: tuple[str, ...] | list[str]) -> str | None:
    if not values:
        return None
    return json.dumps(list(values), ensure_ascii=False)


def _load_list(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return ()
    if not isinstance(parsed, list):
        return ()
    return tuple(str(item) for item in parsed)
