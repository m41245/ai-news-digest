"""
Unit tests for TopicMapper.
"""

from __future__ import annotations

from ai_news_digest.domain.models.topic import Topic
from ai_news_digest.infrastructure.database.mappers.topic_mapper import (
    TopicMapper,
    _slugify,
)
from ai_news_digest.infrastructure.database.models.topic_model import TopicModel


def test_topic_mapper_round_trip() -> None:
    topic = Topic.create(name="AI", slug="ai")

    model = TopicMapper.to_model(topic)

    assert isinstance(model, TopicModel)
    assert model.id == str(topic.id)
    assert model.name == topic.name
    assert model.slug == topic.slug

    restored = TopicMapper.to_domain(model)

    assert restored.id == topic.id
    assert restored.name == topic.name
    assert restored.slug == topic.slug
    assert restored.created_at == topic.created_at


def test_topic_mapper_update_model() -> None:
    topic = Topic.create(name="AI", slug="ai")
    model = TopicModel(
        id=str(topic.id),
        name="Old",
        slug="old",
        created_at=topic.created_at,
        updated_at=topic.created_at,
    )

    TopicMapper.update_model(model, topic)

    assert model.name == "AI"
    assert model.slug == "ai"


def test_topic_mapper_does_not_clear_slug_when_topic_slug_is_none() -> None:
    topic = Topic.create(name="AI", slug=None)
    model = TopicModel(
        id=str(topic.id),
        name="Old",
        slug="existing",
        created_at=topic.created_at,
        updated_at=topic.created_at,
    )

    TopicMapper.update_model(model, topic)

    assert model.name == "AI"
    assert model.slug == "existing"


def test_topic_mapper_slug_lookup_normalization() -> None:
    assert _slugify("AI News & Trends!") == "ai-news-trends"
    assert _slugify("A" * 100) == "a" * 64


def test_topic_mapper_slug_does_not_end_with_hyphen_after_truncation() -> None:
    value = "a" * 63 + " " + "b" * 10
    slug = _slugify(value)
    assert not slug.endswith("-")
    assert slug == "a" * 63


def test_topic_model_name_supports_255_characters() -> None:
    column = TopicModel.__table__.columns["name"]

    assert column.type.length == 255
