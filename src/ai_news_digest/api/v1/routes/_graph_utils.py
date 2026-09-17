"""Shared graph utilities for API route modules."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from ai_news_digest.bootstrap.container import Container


async def build_graph_name_map(
    container: Container,
    relationships: list[Any],
) -> dict[str, str]:
    """Build a map of entity keys to display names for graph connections."""
    name_map: dict[str, str] = {}
    company_ids: list[str] = []
    topic_ids: list[str] = []
    category_ids: list[str] = []
    story_ids: list[str] = []

    for rel in relationships:
        obj_type = rel.object_entity_type.value
        subj_type = rel.subject_entity_type.value
        if obj_type == "company":
            company_ids.append(str(rel.object_entity_id))
        elif obj_type == "topic":
            topic_ids.append(str(rel.object_entity_id))
        elif obj_type == "category":
            category_ids.append(str(rel.object_entity_id))
        elif obj_type == "story":
            story_ids.append(str(rel.object_entity_id))

        if subj_type == "company":
            company_ids.append(str(rel.subject_entity_id))
        elif subj_type == "topic":
            topic_ids.append(str(rel.subject_entity_id))
        elif subj_type == "category":
            category_ids.append(str(rel.subject_entity_id))
        elif subj_type == "story":
            story_ids.append(str(rel.subject_entity_id))

    if company_ids:
        companies = await container.company_repository.list_by_ids(company_ids)
        for c in companies:
            name_map[f"company:{c.id}"] = c.name

    if topic_ids:
        topics = await container.topic_repository.list_by_ids(topic_ids)
        for t in topics:
            name_map[f"topic:{t.id}"] = t.name

    if category_ids:
        unique_cat_ids = list(set(category_ids))
        categories = await container.category_repository.list_by_ids(
            [UUID(cid) for cid in unique_cat_ids]
        )
        for cat in categories:
            name_map[f"category:{cat.id}"] = cat.name

    if story_ids:
        unique_story_ids = list(set(story_ids))
        clusters = await container.story_cluster_repository.get_by_ids(
            [UUID(sid) for sid in unique_story_ids]
        )
        for cluster in clusters:
            name_map[f"story:{cluster.id}"] = cluster.title

    return name_map
