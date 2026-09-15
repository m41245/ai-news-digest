# Milestone 86 — Personalized Intelligence Foundation

## Status: ACCEPTED

## Scope

- Added user preference model with followed/muted entity lists (companies, topics, categories, sources)
- Added source-level follow/mute with dedicated junction tables and migrations
- Added `UserPreferenceRepository` source follow/mute CRUD and entity follow/mute methods
- Added personalized feed use case with story-level candidates, `RankingExplanation`, and deterministic tie-breaking
- Added personalized trends use case with mute-before-score filtering
- Added `PersonalizedRelevanceEngine` deterministic scoring service with bounded score accumulation
- Added frontend `/me/preferences` and `/me/feed` pages with authenticated routing
- Added TypeScript API contracts for preferences, feed, and trend responses

## Deliverables

- `src/ai_news_digest/domain/models/user_preference.py`
- `src/ai_news_digest/domain/ports/user_preference_repository.py`
- `src/ai_news_digest/domain/ports/article_repository.py` (muted source passthrough)
- `src/ai_news_digest/domain/ports/trend_repository.py` (`list_personalized`)
- `src/ai_news_digest/domain/models/trend.py` (related entity IDs)
- `src/ai_news_digest/infrastructure/database/models/user_followed_source_model.py`
- `src/ai_news_digest/infrastructure/database/models/user_muted_source_model.py`
- `src/ai_news_digest/infrastructure/database/models/user_model.py` (source follow/mute relationships)
- `src/ai_news_digest/infrastructure/database/models/trend_model.py` (related entity ID columns)
- `src/ai_news_digest/infrastructure/database/models/source_model.py` (`followed_by_users`, `muted_by_users`)
- `src/ai_news_digest/infrastructure/database/mappers/user_preference_mapper.py`
- `src/ai_news_digest/infrastructure/database/mappers/trend_mapper.py`
- `src/ai_news_digest/infrastructure/database/repositories/user_preference_repository.py`
- `src/ai_news_digest/infrastructure/database/repositories/article_repository.py` (muted source filtering)
- `src/ai_news_digest/infrastructure/database/repositories/trend_repository.py` (`list_personalized`)
- `src/ai_news_digest/application/services/personalization/personalized_relevance_engine.py`
- `src/ai_news_digest/application/use_cases/user_preference/follow_source.py`
- `src/ai_news_digest/application/use_cases/user_preference/mute_source.py`
- `src/ai_news_digest/application/use_cases/trend/get_personalized_trends.py`
- `src/ai_news_digest/application/use_cases/user_preference/get_personalized_feed.py`
- `src/ai_news_digest/application/use_cases/trend/detect_trends.py` (related IDs attachment)
- `src/ai_news_digest/api/v1/routes/user_preferences.py` (source follow/mute, `/me/trends`)
- `src/ai_news_digest/api/v1/schemas/user_preference.py` (followed/muted sources)
- `src/ai_news_digest/bootstrap/container.py` (new use cases registered)
- `migrations/versions/027_add_source_preferences.py`
- `migrations/versions/028_add_trend_related_ids.py`
- `frontend/src/types.ts` (preference, feed, trend types)
- `frontend/src/api/index.ts` (`userPreferenceApi`, `personalizedApi`)
- `frontend/src/pages/dashboard/PreferencesPage.tsx`
- `frontend/src/pages/dashboard/PersonalizedFeedPage.tsx`
- `frontend/src/App.tsx` (`/me/preferences`, `/me/feed` routes)
- `tests/unit/application/services/personalization/test_personalized_relevance_engine.py`
- `tests/unit/application/use_cases/user_preference/test_source_preferences.py`

## Test Results

- M86-specific tests: 97/97 pass
- Full backend unit test suite: 2188/2188 pass
- Migration tests: 10/10 pass
- Frontend: `npm run typecheck` pass, `npm run lint` pass, `npm run build` pass
- MyPy: clean on all changed M86 backend files
- Ruff: clean on all changed M86 files

## Verification Summary

- All `/me/*` routes require `get_current_active_user`; no unauthenticated personalized data exposure
- Mute precedence: muted entities excluded before scoring in feed and trend queries
- Cold start: default empty preferences; no fabricated behavioral history
- Global ranking (`RankingWeights`/`RankingExplanation`) remains untouched; personalization is a separate additive signal
- Bounded candidate limits enforced in feed and trend queries; no N+1 query patterns
- No IDOR: personalized endpoints scoped to authenticated user ID

## Acceptance Criteria

- [x] Users can follow/mute sources, companies, topics, and categories
- [x] Personalized feed re-ranks candidates with deterministic scoring
- [x] Muted entities are excluded before ranking
- [x] Empty preferences produce a valid fallback feed
- [x] Personalized trends respect mute list
- [x] All quality gates pass
- [x] No security regressions
