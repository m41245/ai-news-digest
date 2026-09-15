# Milestone 86 Engineering Report

## Executive Summary

Milestone 86 adds a personalized intelligence foundation to the platform. Users can follow and mute companies, topics, categories, and sources. The personalized feed and trends endpoints re-rank content deterministically while preserving the existing global ranking weights. All personalization logic is additive and does not modify global scoring.

## Architecture

### Domain Layer

- `UserPreference` entity with `followed_company_ids`, `followed_topic_ids`, `followed_category_ids`, `followed_source_ids`, `muted_company_ids`, `muted_topic_ids`, `muted_category_ids`, `muted_source_ids`
- `UserPreferenceRepository` port with source follow/mute CRUD methods
- `ArticleRepository` port extended with `muted_source_ids` passthrough
- `TrendRepository` port extended with `list_personalized`
- `Trend` domain model extended with `related_company_ids`, `related_topic_ids`, `related_category_ids`

### Infrastructure Layer

- New SQLAlchemy models: `UserFollowedSourceModel`, `UserMutedSourceModel`
- Updated `UserModel` with source follow/mute relationships
- Updated `SourceModel` with `followed_by_users` and `muted_by_users`
- Updated `TrendModel` with related entity ID columns
- Mappers serialize/deserialize related IDs and preference links
- Repositories implement muted source filtering and personalized trend queries

### Application Layer

- `PersonalizedRelevanceEngine`: deterministic scoring service with bounded accumulator
- `FollowSourceUseCase`, `UnfollowSourceUseCase`, `MuteSourceUseCase`, `UnmuteSourceUseCase`
- `GetPersonalizedFeedUseCase`: story-level candidates, `RankingExplanation`, tie-breaking
- `GetPersonalizedTrendsUseCase`: mute-before-score filtering
- `DetectTrendsUseCase`: attaches related IDs to trend candidates

### API Layer

- `/api/v1/me/preferences` — GET/PATCH preferences, follow/mute companies/topics/categories/sources
- `/api/v1/me/feed` — personalized article feed
- `/api/v1/me/trends` — personalized trends
- All `/me/*` routes protected by `get_current_active_user`

### Frontend

- `/me/preferences` — preference management page
- `/me/feed` — personalized feed page
- TypeScript API clients: `userPreferenceApi`, `personalizedApi`
- Types for preference, feed item, and trend responses

## Data Model Changes

- Migration 027: `user_followed_sources`, `user_muted_sources` junction tables with composite unique constraints
- Migration 028: `trends.related_company_ids`, `trends.related_topic_ids`, `trends.related_category_ids`

## Personalization Semantics

- **Mute precedence**: muted entities are excluded before scoring in both feed and trend queries
- **Follow boost**: followed entities add positive scoring signals via `PersonalizedRelevanceEngine`
- **Cold start**: default empty preferences; no fabricated behavioral history
- **Global ranking preservation**: `RankingWeights`/`RankingExplanation` remain untouched; personalization is a separate additive signal
- **Deterministic tie-breaking**: stable ordering by `id` when scores are equal

## Performance

- Story-level candidate queries bound results at the database layer
- Mute lists pushed to SQL `WHERE` clauses to minimize Python-side filtering
- No N+1 patterns in personalized feed or trend queries

## Security

- All personalized endpoints require authentication
- User-scoped queries prevent cross-user data leakage
- No IDOR vulnerabilities: preferences and feed always scoped to `current_user.id`

## Quality Gates

| Gate | Result |
|------|--------|
| M86 tests | 97/97 pass |
| Backend unit tests | 2188/2188 pass |
| Migration tests | 10/10 pass |
| MyPy (changed files) | Clean |
| Ruff (changed files) | Clean |
| Frontend typecheck | Pass |
| Frontend lint | Pass |
| Frontend build | Pass |

## Committed Files

25 modified, 6 new untracked (excluding pre-existing documentation files).

## Conclusion

**M86 ACCEPTED.** Personalized intelligence foundation is complete, tested, and ready for integration.
