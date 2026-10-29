from __future__ import annotations

import re
import unicodedata
from uuid import UUID

from ai_news_digest.domain.models.topic import Topic
from ai_news_digest.infrastructure.database.models.topic_model import TopicModel


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    result = (slug or "topic")[:64].rstrip("-")
    return result or "topic"


class TopicMapper:
    @staticmethod
    def to_model(topic: Topic) -> TopicModel:
        slug = topic.slug or _slugify(topic.name)
        return TopicModel(
            id=str(topic.id),
            name=topic.name,
            slug=slug,
            created_at=topic.created_at,
            updated_at=topic.created_at,
        )

    @staticmethod
    def to_domain(model: TopicModel) -> Topic:
        return Topic(
            id=UUID(model.id),
            name=model.name,
            created_at=model.created_at,
            slug=getattr(model, "slug", None),
            article_count=getattr(model, "article_count", 0) or 0,
        )

    @staticmethod
    def update_model(model: TopicModel, topic: Topic) -> None:
        model.name = topic.name
        if topic.slug:
            model.slug = topic.slug
