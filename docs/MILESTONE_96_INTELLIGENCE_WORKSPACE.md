# M96 — Intelligence Workspace, Saved Intelligence & User Experience

## Objective

Build the personal intelligence workspace layer on top of the existing AI News Intelligence Platform.

## What Was Built

### Backend

#### Domain Models
- `SavedStory` — user saves a story cluster with optional note and collection
- `UserCollection` — user-defined collection for organizing saved stories
- `FollowedStory` — user follows a story cluster to track evolution

#### Database
- Alembic migration `033_add_saved_intelligence.py`
- Tables: `saved_stories`, `user_collections`, `followed_stories`
- Foreign keys to `users` and `story_clusters` with CASCADE delete
- Unique constraints: `uq_user_saved_story`, `uq_user_followed_story`, `uq_user_collection_name`

#### API Endpoints
```
POST   /api/v1/me/saved-stories          Save a story cluster
GET    /api/v1/me/saved-stories          List saved stories (supports collection filter)
DELETE /api/v1/me/saved-stories/{id}     Unsave a story

POST   /api/v1/me/collections            Create collection
GET    /api/v1/me/collections            List collections
PATCH  /api/v1/me/collections/{id}       Update collection
DELETE /api/v1/me/collections/{id}       Delete collection

POST   /api/v1/me/followed-stories/{id}  Follow a story cluster
DELETE /api/v1/me/followed-stories/{id}  Unfollow a story cluster
GET    /api/v1/me/followed-stories       List followed stories
```

#### Use Cases
- `SaveStoryUseCase` — saves a story, raises `DuplicateResourceError` if already saved
- `UnsaveStoryUseCase` — removes a saved story
- `ListSavedStoriesUseCase` — paginated list with optional collection filter
- `CreateCollectionUseCase` — creates collection, raises `DuplicateResourceError` if name exists
- `UpdateCollectionUseCase` — updates collection name/description
- `DeleteCollectionUseCase` — deletes collection
- `ListCollectionsUseCase` — paginated list of user collections
- `FollowStoryUseCase` — follows a story, raises `DuplicateResourceError` if already following
- `UnfollowStoryUseCase` — unfollows a story
- `ListFollowedStoriesUseCase` — paginated list of followed stories

### Frontend

#### Routes
- `/me` — IntelligenceWorkspacePage (replaces DashboardPage for authenticated users)
- `/me/saved` — SavedStoriesPage
- `/me/following` — FollowedStoriesPage

#### Components
- `IntelligenceWorkspacePage` — unified workspace with saved stories, followed stories, top story, account info
- `SavedStoriesPage` — collection filtering, unsave action, note display
- `FollowedStoriesPage` — story details with status/importance, unfollow action
- `StoryClusterPage` — Save/Follow buttons for authenticated users

#### Navigation
- Header updated with Saved and Following links for authenticated users

## Design Decisions

1. **StoryCluster-first**: Saved items reference `StoryCluster` rather than individual `Article` instances, avoiding duplicate article storage
2. **Generic collections**: `UserCollection` is a generic model, not hardcoded "Saved"/"Watchlist"/"Research"/"Follow-up"
3. **Deterministic ordering**: Saved stories ordered by `created_at DESC`, followed stories ordered by `created_at DESC`
4. **No behavioral tracking**: Follow/save actions are explicit user actions; no inference from reading behavior
5. **No new AI calls**: All features are database-driven; works with `AI_ENABLED=false`
6. **No new caching**: User-specific data not cached (would require cache-key user isolation)
7. **Unique constraints**: Database-level uniqueness prevents duplicate saves/follows/collection names

## Security

- All endpoints require authentication via `get_current_active_user`
- User identity derived from JWT token, never from client input
- All queries filtered by `user_id` from authenticated context
- IDOR protection via ownership checks
- Collection names bounded to 100 characters
- Notes bounded by TEXT column

## Testing

### Backend
- 13 new unit tests for use cases (mocked repositories)
- Tests cover: create, duplicate prevention, delete, list, pagination

### Frontend
- All 40 existing frontend tests pass
- StoryClusterPage tests updated to wrap in `AuthProvider`

## Pre-existing Issues

- UP037 (quoted type annotations) in existing models — not introduced by M96
- UP046 in `PaginatedResponse` — pre-existing
- B904, S112 in existing AI code — pre-existing

## Files Changed

### Backend
- `migrations/versions/033_add_saved_intelligence.py`
- `src/ai_news_digest/domain/models/saved_story.py`
- `src/ai_news_digest/domain/models/user_collection.py`
- `src/ai_news_digest/domain/models/followed_story.py`
- `src/ai_news_digest/domain/ports/saved_story_repository.py`
- `src/ai_news_digest/domain/ports/user_collection_repository.py`
- `src/ai_news_digest/domain/ports/followed_story_repository.py`
- `src/ai_news_digest/infrastructure/database/models/saved_story_model.py`
- `src/ai_news_digest/infrastructure/database/models/user_collection_model.py`
- `src/ai_news_digest/infrastructure/database/models/followed_story_model.py`
- `src/ai_news_digest/infrastructure/database/models/user_model.py`
- `src/ai_news_digest/infrastructure/database/models/__init__.py`
- `src/ai_news_digest/infrastructure/database/repositories/saved_story_repository.py`
- `src/ai_news_digest/infrastructure/database/repositories/user_collection_repository.py`
- `src/ai_news_digest/infrastructure/database/repositories/followed_story_repository.py`
- `src/ai_news_digest/application/use_cases/saved_story/save_story.py`
- `src/ai_news_digest/application/use_cases/user_collection/manage_collections.py`
- `src/ai_news_digest/application/use_cases/followed_story/manage_followed_stories.py`
- `src/ai_news_digest/api/v1/schemas/intelligence_workspace.py`
- `src/ai_news_digest/api/v1/routes/intelligence_workspace.py`
- `src/ai_news_digest/bootstrap/container.py`
- `src/ai_news_digest/main.py`

### Frontend
- `frontend/src/types.ts`
- `frontend/src/api/index.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/layout/Header.tsx`
- `frontend/src/pages/public/StoryClusterPage.tsx`
- `frontend/src/pages/dashboard/IntelligenceWorkspacePage.tsx`
- `frontend/src/pages/dashboard/SavedStoriesPage.tsx`
- `frontend/src/pages/dashboard/FollowedStoriesPage.tsx`

### Documentation
- `docs/MILESTONE_96_INTELLIGENCE_WORKSPACE.md`
- `docs/PROJECT_STATUS.md`

## Verification

- Ruff: passes on all M96 files (pre-existing issues in other files)
- MyPy: passes on all M96 files
- TypeScript: passes with no errors
- Frontend tests: 40/40 pass
- Backend unit tests: 13/13 new tests pass, 70+ existing tests pass
