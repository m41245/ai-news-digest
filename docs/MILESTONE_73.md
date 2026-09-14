# Milestone 73 — Production UX, Performance, Accessibility & SEO Hardening

## Status: COMPLETE

M73 focuses on hardening the existing public news intelligence experience. No AI providers were activated. No new infrastructure was introduced. All work reuses the existing FastAPI + PostgreSQL + React + Tailwind architecture.

## What Changed

### Frontend UX
- **Header**: Added responsive mobile navigation with hamburger toggle, keyboard accessibility (Escape to close), click-outside-to-close, and `aria-expanded` state.
- **Footer**: Replaced `<a>` tags with `react-router-dom` `Link` components for internal navigation to avoid full page reloads.
- **Landing Page**: Replaced loading spinner with skeleton UI for Top Story and Latest Digest sections. Improved SEO title to "AI News Digest — News distilled by AI". Added Open Graph metadata and canonical URL.
- **Article Detail**: Replaced full-page spinner with skeleton loading state matching article card layout.
- **Digest Detail**: Replaced full-page spinner with skeleton loading state. Added empty state for digests with no stories.
- **Story Cluster**: Replaced full-page spinner with skeleton loading state. Fixed `JSON.stringify(c)` rendering of contradictions to render structured objects safely. Added empty state for clusters with no recent articles.
- **News Page**: Replaced inline filter buttons with a collapsible filter panel. Filters are open by default on desktop; mobile users can collapse/expand. Added visual active-filter indicator dot on the toggle button. Improved active filter chip accessibility with `aria-label` on remove buttons.
- **SEO**: Added canonical URLs to News, Digests, Categories, Companies, and Topics pages. Improved NotFoundPage description.

### Loading States
- Added `ArticleCardSkeleton`, `DigestCardSkeleton`, `StoryCardSkeleton`, and `TopStorySkeleton` variants to the shared `Skeleton` component.
- All public API-driven pages now use skeleton loading instead of full-page spinners where appropriate.
- Skeleton loading respects reduced-motion preferences via existing CSS `animate-pulse`.

### Error States
- API client (`client.ts`) now sanitizes error responses:
  - 500+ errors return a generic "Something went wrong on our end" message instead of exposing internal details.
  - 404, 429, 403, and 401 errors return user-friendly messages.
- Error boundary behavior unchanged; backend exception handlers already suppress internal details in production.

### Empty States
- Digest detail page shows an empty state when a digest has no stories.
- Story cluster page shows an empty state when a cluster has no recent articles.
- News page empty state already existed and remains intact.

### Accessibility
- Mobile menu uses `role="menu"` and `role="menuitem"` semantics.
- Mobile toggle has `aria-expanded` and `aria-label`.
- Active filter remove buttons have descriptive `aria-label` attributes.
- Skip-to-content link remains functional.

### SEO
- Landing page title improved from generic "AI News Digest" to "AI News Digest — News distilled by AI".
- Added `og:url` and `og:image` support to the shared `Seo` component.
- Public story/digest/article pages retain their meaningful metadata.
- NotFoundPage includes `noindex` and a description.

### Backend Performance
- `public.py`: Added `lru_cache` to `_build_source_and_category_maps` to avoid repeated database queries for source/category lookups across article list and detail requests.
- `public.py`: Replaced sequential per-digest `_build_top_story` queries in `list_public_digests` with `asyncio.gather` for parallel cluster lookups.
- `public.py`: Fixed `source_map` and `source_type_map` key types to use `str` consistently, avoiding UUID/str mismatch issues.

### Tests Added
- `frontend/tests/components/Header.test.tsx`: 6 tests covering mobile menu rendering, toggle behavior, Escape key handling, and `aria-expanded`.
- `frontend/tests/integration/NewsPageFilters.test.tsx`: 4 tests covering filter toggle visibility, collapse/expand behavior, and active filter indicators.

## Files Changed

### Frontend
- `frontend/src/api/client.ts` — Error sanitization
- `frontend/src/components/Seo.tsx` — `og:image` and `og:url` support
- `frontend/src/components/layout/Header.tsx` — Mobile navigation
- `frontend/src/components/layout/Footer.tsx` — `Link` for internal nav
- `frontend/src/components/ui/Skeleton.tsx` — New skeleton variants
- `frontend/src/pages/public/LandingPage.tsx` — Skeleton loading, SEO
- `frontend/src/pages/public/NewsPage.tsx` — Collapsible filters, skeleton loading
- `frontend/src/pages/public/ArticleDetailPage.tsx` — Skeleton loading
- `frontend/src/pages/public/DigestDetailPage.tsx` — Skeleton loading, empty state
- `frontend/src/pages/public/StoryClusterPage.tsx` — Skeleton loading, contradiction rendering fix, empty state
- `frontend/src/pages/public/DigestsPage.tsx` — Canonical URL
- `frontend/src/pages/public/CompaniesPage.tsx` — Canonical URL
- `frontend/src/pages/public/TopicsPage.tsx` — Canonical URL
- `frontend/src/pages/public/CategoriesPage.tsx` — Canonical URL
- `frontend/src/pages/public/NotFoundPage.tsx` — Description SEO
- `frontend/tests/components/Header.test.tsx` — New
- `frontend/tests/integration/NewsPageFilters.test.tsx` — New

### Backend
- `src/ai_news_digest/api/v1/routes/public.py` — N+1 reduction, source/category map caching, type fixes

## Database Changes

No database migration required. No schema changes.

## New Dependencies

None.

## Security Verification

- Public endpoints remain public-only where intended.
- Admin endpoints remain protected.
- Authentication unchanged.
- CORS unchanged.
- No credentials exposed in frontend bundles.
- No secrets in logs.
- No internal stack traces returned to clients.
- URL parameters validated by existing FastAPI `Query` constraints.
- Search input bounded by `max_length=200`.
- Pagination bounded by `MAX_PAGE_LIMIT=100` and `MAX_OFFSET=10_000`.
- External publisher links use `rel="noopener noreferrer"`.
- No arbitrary URL fetching introduced into the frontend.
- SSRF protections untouched.

## AI Status

`AI_ENABLED=false` remains the safe default. No real provider activation occurred. No paid AI calls were made. No fabricated AI output was introduced.

## Test Results

### Frontend
- TypeScript: `tsc -b --noEmit` passes cleanly.
- ESLint: passes cleanly.
- Production build: succeeds (26.92 kB CSS, 143.62 kB JS main bundle gzip: 40.44 kB).
- Tests: 35 passed, 0 failed.

### Backend
- Public API tests: 17 passed.
- Health/config tests: 77 passed.
- Full unit suite: 696 passed (1 pre-existing test isolation failure in `test_generate_intelligent_digest.py` when run in batch; passes individually).

### Static Analysis
- `ruff check` on changed files: all checks passed.
- `ruff format --check` on changed files: all checks passed.
- `mypy` on `public.py`: no new errors.

## Known Limitations

- Pre-existing batch test isolation failure in `tests/unit/application/use_cases/digest/test_generate_intelligent_digest.py::test_existing_digest_reused_when_not_forced`. This test passes when run individually. Root cause is test-order-dependent state pollution, not an M73 regression.
- Pre-existing `mypy` errors in `generate_intelligent_digest.py` and `digest.py` (40 errors in 8 files) are unrelated to M73.
- Pre-existing `ruff` formatting differences across 38 files are unrelated to M73.
- Docker/Testcontainers/PostgreSQL are not available in this environment; integration tests requiring a running database were not executed.

## Recommended Next Milestone

M74 or M75 should focus on real AI provider activation (`AI_ENABLED=true`), personalized feeds, or notification enhancements per the project roadmap. M73's hardening work provides a stable foundation for those features.
