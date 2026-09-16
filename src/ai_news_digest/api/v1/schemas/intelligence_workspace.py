from __future__ import annotations

from pydantic import BaseModel


class SaveStoryRequest(BaseModel):
    story_cluster_id: str
    collection_id: str | None = None
    note: str | None = None


class SavedStoryResponse(BaseModel):
    id: str
    user_id: str
    story_cluster_id: str
    collection_id: str | None = None
    note: str | None = None
    created_at: str | None = None


class CollectionCreateRequest(BaseModel):
    name: str
    description: str | None = None


class CollectionUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class CollectionResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class FollowedStoryResponse(BaseModel):
    id: str
    user_id: str
    story_cluster_id: str
    created_at: str | None = None
