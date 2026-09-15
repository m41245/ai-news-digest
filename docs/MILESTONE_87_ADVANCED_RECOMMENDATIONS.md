# Milestone 87 — Advanced Recommendation Intelligence

## Status: ACCEPTED

## Scope

- Added deterministic recommendation engine combining global importance, M86 personal relevance, freshness, story activity, trend momentum, story evolution, diversity, and novelty into a bounded 0-100 `recommendation_score`
- Added `GetRecommendationsUseCase` orchestrating candidate retrieval, scoring, diversity selection, and response building
- Added authenticated API endpoint `GET /api/v1/me/recommendations`
- Added frontend `RecommendationsPage` at `/me/recommendations`
- Reused existing M86 personalization architecture without rebuilding it
- Kept global `ranking_score` separate from new `recommendation_score`

## Deliverables

- `src/ai_news_digest/application/services/recommendation/constants.py`
- `src/ai_news_digest/application/services/recommendation/recommendation_engine.py`
- `src/ai_news_digest/application/use_cases/recommendation/get_recommendations.py`
- `src/ai_news_digest/api/v1/routes/recommendations.py`
- `src/ai_news_digest/api/v1/schemas/recommendation.py`
- `src/ai_news_digest/bootstrap/container.py` (DI registration)
- `src/ai_news_digest/main.py` (router registration)
- `src/ai_news_digest/domain/ports/story_cluster_repository.py` (`get_by_ids`)
- `src/ai_news_digest/domain/ports/story_activity_repository.py` (`get_by_cluster_ids`)
- `src/ai_news_digest/domain/ports/story_event_repository.py` (`list_by_cluster_ids`)
- `frontend/src/pages/dashboard/RecommendationsPage.tsx`
- `frontend/src/api/index.ts` (`personalizedApi.recommendations`)
- `frontend/src/types.ts` (`RecommendationItemResponse`, `RecommendationResponse`)
- `tests/unit/application/services/recommendation/test_recommendation_engine.py`
- `tests/unit/application/use_cases/recommendation/test_get_recommendations.py`
- `tests/unit/api/v1/routes/test_recommendations.py`

## Test Results

- M87-specific tests: 23/23 pass
- Full backend unit test suite: 1613/1613 pass (1 pre-existing pytest-asyncio fixture error unrelated to M87)
- Frontend: `npm run typecheck` pass, `npm run lint` pass
- MyPy: clean on all changed M87 backend files
- Ruff: clean on all changed M87 files

## Verification Summary

- Endpoint `GET /api/v1/me/recommendations` returns paginated, scored recommendations with explainable signals
- `recommendation_score` is bounded 0-100 and deterministic for identical inputs
- Global `ranking_score` is preserved separately; recommendation scoring is additive and independent
- Diversity selection prevents excessive same-company/topic/category/source concentration
- Activity-aware scoring uses `StoryActivity` status (breaking/developing/ongoing/stale)
- Trend-aware scoring uses `Trend` momentum and trend scores
- Mute precedence: muted entities excluded before scoring
- Cold start: empty preferences produce valid fallback recommendations
- No behavioral tracking, no collaborative filtering, no embeddings

## Acceptance Criteria

- [x] Users see personalized recommendations at `/me/recommendations`
- [x] Recommendation scores are deterministic and explainable
- [x] Global ranking score remains separate from recommendation score
- [x] Diversity selection reduces over-concentration
- [x] Story activity and trend momentum influence scores
- [x] Muted entities are excluded before scoring
- [x] All quality gates pass
- [x] No security regressions
