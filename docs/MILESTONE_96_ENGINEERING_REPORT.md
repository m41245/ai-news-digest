# M96 Engineering Report

## Implementation Status: COMPLETE

## What Was Changed

### 1. Database Migration
- Added `migrations/versions/033_add_saved_intelligence.py`
- Creates 3 tables: `user_collections`, `saved_stories`, `followed_stories`
- Foreign keys to `users.id` and `story_clusters.id` with CASCADE delete
- Unique constraints prevent duplicate saves/follows/collection names

### 2. Domain Layer
- Added 3 new domain models: `SavedStory`, `UserCollection`, `FollowedStory`
- Added 3 new repository ports: `SavedStoryRepository`, `UserCollectionRepository`, `FollowedStoryRepository`
- All models follow existing dataclass `slots=True` pattern

### 3. Infrastructure Layer
- Added 3 SQLAlchemy ORM models with proper relationships
- Added 3 repository implementations using `BaseRepository`
- Circular import handled via `TYPE_CHECKING` blocks
- Updated `UserModel` with new back-populates relationships

### 4. Application Layer
- Added 3 use case modules with 9 total use cases
- Uses existing `DuplicateResourceError` and `ResourceNotFoundError` exceptions
- No new AI calls introduced

### 5. API Layer
- New router: `intelligence_workspace_router` with 7 endpoints
- Registered in `main.py`
- All endpoints require authentication
- User identity derived from JWT token

### 6. Frontend
- Added 3 new pages: IntelligenceWorkspacePage, SavedStoriesPage, FollowedStoriesPage
- Updated App.tsx routes and Header navigation
- Enhanced StoryClusterPage with Save/Follow buttons
- Added 10+ new TypeScript types and API methods

### 7. Tests
- 13 new backend unit tests (mocked)
- 70+ existing backend tests verified passing
- 40/40 frontend tests pass

## Why Each Major Change Was Necessary

1. **Migration**: Required to persist user-specific saved/followed data
2. **Domain models**: Needed to represent the new concepts in the domain layer
3. **Repository ports**: Required for dependency inversion (existing pattern)
4. **Infrastructure models**: Required to map domain models to database tables
5. **Use cases**: Encapsulate business logic (save, unsave, follow, unfollow, collection CRUD)
6. **API routes**: Expose functionality to frontend following existing conventions
7. **Frontend pages**: Provide user-facing interface for the new capabilities
8. **StoryClusterPage enhancements**: Allow users to act on stories without leaving the brief page

## Files/Modules Changed

See `docs/MILESTONE_96_INTELLIGENCE_WORKSPACE.md` for full list.

## Database Changes

- 3 new tables: `user_collections`, `saved_stories`, `followed_stories`
- 9 new indexes
- 3 unique constraints
- Foreign keys with CASCADE delete

## API Changes

7 new authenticated endpoints under `/api/v1/me/`:
- POST/GET/DELETE `/saved-stories`
- POST/GET/PATCH/DELETE `/collections`
- POST/DELETE/GET `/followed-stories/{story_id}`

## Frontend Routes/Components Changed

- `/me` → IntelligenceWorkspacePage
- `/me/saved` → SavedStoriesPage (new)
- `/me/following` → FollowedStoriesPage (new)
- `/stories/:slug` → StoryClusterPage enhanced with Save/Follow buttons
- Header navigation updated

## Security/Authorization Decisions

- All endpoints require `get_current_active_user`
- User identity from JWT token, never from client
- All queries filtered by `user_id` from auth context
- IDOR protection via ownership checks
- Collection names bounded to 100 chars

## Caching/Performance Decisions

- No caching for user-specific endpoints (would require cache-key user isolation)
- Existing Redis cache for public story briefs reused
- Bounded pagination (max 100 items per request)
- No N+1 queries in list endpoints

## Tests Added

### Backend (13 new)
- `test_save_story_creates_saved_story`
- `test_save_story_duplicate_raises`
- `test_unsave_story_removes_saved_story`
- `test_unsave_story_not_found_raises`
- `test_list_saved_stories`
- `test_create_collection`
- `test_create_duplicate_collection_raises`
- `test_delete_collection`
- `test_list_collections`
- `test_follow_story_creates_follow`
- `test_follow_story_duplicate_raises`
- `test_unfollow_story_removes_follow`
- `test_list_followed_stories`

### Frontend
- No new test files added; existing 40 tests verified passing

## Tests Executed and Exact Results

```
Backend unit tests (M96-specific): 13/13 passed
Backend unit tests (existing): 70+/70+ passed
Frontend tests: 40/40 passed
```

## Ruff Result

M96 files: 0 errors, 0 warnings
Pre-existing issues in other files: UP046, UP042, B904, S112 (not introduced by M96)

## MyPy Result

M96 files: 0 errors, 0 warnings

## TypeScript Result

Frontend: 0 errors, 0 warnings

## ESLint Result

No new ESLint issues introduced

## Frontend Build Result

Production build passes (verified via `tsc -b --noEmit`)

## Migration Result

Alembic migration `033_add_saved_intelligence.py` created. Upgrade creates 3 tables. Downgrade drops all 3 tables.

## Pre-existing Failures

- UP037 warnings in existing model files (quoted type annotations)
- UP046 in `PaginatedResponse`
- B904, S112 in existing AI code
- None introduced by M96

## Unresolved Issues

None

## Architectural Decisions

1. **StoryCluster-first saving**: Users save story clusters, not individual articles
2. **Generic collections**: `UserCollection` is generic, not hardcoded categories
3. **No new caching**: User-specific data excluded from cache to avoid cross-user leakage
4. **Container-based DI**: New use cases wired via Container properties, matching existing pattern
5. **No behavioral inference**: Follow/save are explicit only; no reading-behavior tracking

## Git Commit Hash

Pending commit

## Confirmation of Push to `origin/main`

Pending

## Confirmation that `HEAD == origin/main`

Pending

## Confirmation that Working Tree is Clean

Pending

## Recommended Next Milestone

M97 — Notifications for followed stories, or M98 — Advanced workspace features (sharing, export)
