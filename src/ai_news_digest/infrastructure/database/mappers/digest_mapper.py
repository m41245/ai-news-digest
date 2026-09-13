from __future__ import annotations

import json
from uuid import UUID

from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.infrastructure.database.models.digest_model import (
    DigestModel,
)


class DigestMapper:
    """
    Maps between Digest domain objects and DigestModel ORM entities.
    """

    @staticmethod
    def to_model(
        digest: Digest,
    ) -> DigestModel:
        """
        Convert a domain Digest into an ORM DigestModel.
        """
        stories_json = None
        if digest.stories:
            try:
                stories_json = json.dumps(digest.stories)
            except (TypeError, ValueError):
                stories_json = None

        metadata_json = None
        if digest.generation_metadata:
            try:
                metadata_json = json.dumps(digest.generation_metadata)
            except (TypeError, ValueError):
                metadata_json = None

        return DigestModel(
            id=str(digest.id),
            title=digest.title,
            content=digest.content,
            format=digest.format,
            generated_at=digest.generated_at,
            top_story_cluster_id=(
                str(digest.top_story_cluster_id)
                if digest.top_story_cluster_id is not None
                else None
            ),
            stories=stories_json,
            generation_metadata=metadata_json,
            generation_method=digest.generation_method,
            provider=digest.provider,
            model=digest.model,
        )

    @staticmethod
    def to_domain(
        model: DigestModel,
    ) -> Digest:
        """
        Convert an ORM DigestModel into a domain Digest.

        The article_ids are populated from the DigestArticleModel
        relationship if it has been loaded.
        """
        stories = []
        if model.stories:
            try:
                stories = json.loads(model.stories)
            except (TypeError, ValueError):
                stories = []

        generation_metadata = {}
        if model.generation_metadata:
            try:
                generation_metadata = json.loads(model.generation_metadata)
            except (TypeError, ValueError):
                generation_metadata = {}

        return Digest(
            id=UUID(model.id),
            title=model.title,
            content=model.content,
            generated_at=model.generated_at,
            format=(
                DigestFormat(model.format) if model.format is not None else DigestFormat.MARKDOWN
            ),
            article_ids=[UUID(link.article_id) for link in getattr(model, "digest_articles", [])],
            top_story_cluster_id=(
                UUID(model.top_story_cluster_id) if model.top_story_cluster_id is not None else None
            ),
            stories=stories,
            generation_metadata=generation_metadata,
            generation_method=model.generation_method,
            provider=model.provider,
            model=model.model,
        )

    @staticmethod
    def update_model(
        model: DigestModel,
        digest: Digest,
    ) -> None:
        """
        Update an existing ORM model from a domain Digest.
        """
        model.title = digest.title
        model.content = digest.content
        model.format = digest.format
        model.generated_at = digest.generated_at
        model.top_story_cluster_id = (
            str(digest.top_story_cluster_id) if digest.top_story_cluster_id is not None else None
        )

        if digest.stories:
            try:
                model.stories = json.dumps(digest.stories)
            except (TypeError, ValueError):
                model.stories = None
        else:
            model.stories = None

        if digest.generation_metadata:
            try:
                model.generation_metadata = json.dumps(digest.generation_metadata)
            except (TypeError, ValueError):
                model.generation_metadata = None
        else:
            model.generation_metadata = None

        model.generation_method = digest.generation_method
        model.provider = digest.provider
        model.model = digest.model
