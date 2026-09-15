# M88 Semantic Intelligence and Embedding-Ready Discovery

## Executive Summary

Milestone 88 introduces provider-independent semantic intelligence to the AI News Digest platform. The implementation adds an embedding abstraction layer, cosine similarity engine, hybrid search (lexical + semantic), and related story discovery—all while maintaining graceful degradation when AI is disabled (`AI_ENABLED=false`) and without adding new infrastructure dependencies like pgvector.

**Commit:** 8afacbbb6347c389abbd75e377a3f4780b7ab180  
**Branch:** main  
**Status:** COMPLETE (M88.1 audited and hardened)

## M88.1 Audit Summary

M88.1 identified and corrected critical architectural bypasses in the original M88 implementation:

### Corrected Defects (P1)

1. **M78 Circuit Breaker Bypass** — `EmbeddingService._select_provider()` did not check `ProviderHealthRegistry`. Fixed: health eligibility is now checked before provider selection; failures are recorded in the health registry.

2. **M79 Quota/Cost Bypass** — `EmbeddingService._select_provider()` did not check `ProviderQuotaRegistry`. Fixed: quota eligibility is checked before provider selection; usage is recorded in the quota registry.

3. **No Provider Fallback** — When the selected provider failed, the exception propagated without trying alternative providers. Fixed: `generate()` and `generate_batch()` now try the selected provider first, then fall back to other available providers.

4. **No Capability Registration** — `EMBEDDING` capability was not registered in `CapabilityRegistry`. Fixed: capability is registered and associated with embedding providers.

5. **Related Stories Fallback to Arbitrary Candidates** — When semantic search returned no results, arbitrary input clusters were returned as "related stories". Fixed: empty list is returned when no semantic signal exists.

6. **Query Length Not Enforced** — `semantic_search_query_max_length` was configured but not enforced in the API. Fixed: queries are truncated to the configured limit in the semantic search path.

## What Was Done

### Backend

1. **Domain Model** (`src/ai_news_digest/domain/models/semantic_document.py`)
   - `SemanticDocument`: bounded semantic content for embedding (id, title, summary, why_it_matters, topics, companies, categories)

2. **Embedding Abstraction** (`src/ai_news_digest/domain/ports/embedding_provider.py`)
   - `EmbeddingProvider`: provider-independent interface independent from `AIProvider`
   - `EmbeddingResponse`: result DTO with embedding, model, dimension, provider, usage_tokens
   - Abstract methods: `embed()`, `embed_batch()`, `dimension`, `model_name`, `priority()`

3. **Application Layer** (`src/ai_news_digest/application/ai/`)
   - `embedding_models.py`: `BatchEmbeddingResult` for batch operations
   - `embedding_provider.py`: `BaseEmbeddingProvider` with dimension validation and error translation
   - `embedding_service.py`: `EmbeddingService` for provider selection (highest priority), single/batch generation, availability check
   - `similarity_engine.py`: `SimilarityEngine` with validated cosine similarity, clamped to [0, 1], never returns NaN/Infinity
   - `semantic_search_service.py`: `SemanticSearchService` for hybrid article/cluster search with configurable weights

4. **Infrastructure** (`src/ai_news_digest/infrastructure/embedding/`)
   - `openai_embedding_provider.py`: `OpenAIEmbeddingProvider` implementation
   - Supports `text-embedding-3-small` (default, 1536 dims)
   - Health check, batch embedding, dimension validation

5. **Related Stories** (`src/ai_news_digest/application/services/related_story_finder.py`)
   - `RelatedStoryFinder`: discovers related story clusters for a given article
   - Combines duplicate detection with semantic similarity
   - Excludes current cluster, respects limit

6. **API Extensions** (`src/ai_news_digest/api/v1/`)
   - `schemas/public.py`: `RelatedStoryResponse`
   - `routes/public.py`: 
     - `GET /api/v1/public/articles?mode=lexical|semantic|hybrid` (default: lexical)
     - `GET /api/v1/public/articles/{id}/related` — related story clusters

7. **Configuration** (`src/ai_news_digest/core/config.py`)
   - `semantic_search_enabled`: bool (default: false)
   - `embedding_model`: str (default: "text-embedding-3-small")
   - `embedding_dimension`: int (default: 1536)
   - `semantic_lexical_weight`, `semantic_similarity_weight`, `semantic_importance_weight`, `semantic_recency_weight`

8. **Container** (`src/ai_news_digest/bootstrap/container.py`)
   - Wired `_embedding_providers`, `embedding_service`, `semantic_search_service`, `related_story_finder`

### Frontend

1. **Types** (`frontend/src/types.ts`)
   - Added `RelatedStoryResponse` interface

2. **API Client** (`frontend/src/api/index.ts`)
   - Added `publicApi.relatedStories(id, limit)`

3. **NewsPage** (`frontend/src/pages/public/NewsPage.tsx`)
   - Added search mode selector: Keyword / Hybrid / Semantic

4. **ArticleDetailPage** (`frontend/src/pages/public/ArticleDetailPage.tsx`)
   - Added Related Stories section

### Tests

- `tests/unit/application/ai/test_similarity_engine.py`: 9 tests (identical, orthogonal, opposite, zero vectors, dimension mismatch, empty vectors, normalized similarity, partial overlap)
- `tests/unit/application/ai/test_embedding_service.py`: 6 tests (no providers, no enabled providers, generates embedding, priority selection, batch, availability)
- `tests/unit/application/ai/test_semantic_search_service.py`: 5 tests (empty candidates, fallback, scored articles, empty clusters, scored clusters)
- `tests/unit/application/services/test_related_story_finder.py`: 4 tests (empty clusters, excludes current, returns related, respects limit)

Total: 24 new tests, all passing.

## Architecture Decisions

### Provider Independence

The `EmbeddingProvider` interface is completely independent from `AIProvider`. A provider may implement both, but they are registered and selected independently. This allows future embedding providers (Cohere, HuggingFace, local models) without touching the generation provider layer.

### M78/M79 Integration

Embedding providers participate in the existing provider health and quota infrastructure:
- `ProviderHealthRegistry` tracks embedding provider success/failure and circuit breaker state
- `ProviderQuotaRegistry` tracks embedding usage and enforces quota limits
- `EmbeddingService` selects providers based on health eligibility, quota eligibility, and priority
- Failed providers trigger circuit breaker state transitions
- Quota exhaustion prevents further embedding requests

### Provider Fallback

When the primary embedding provider fails (timeout, rate limit, circuit open, quota exhausted), `EmbeddingService` falls back to the next available healthy provider. This follows the same bounded fallback pattern used by `ProviderManager` for generation requests.

### Graceful Degradation

- `AI_ENABLED=false` → semantic features are no-ops, lexical search continues normally
- No embedding provider available → `SemanticSearchService` returns zero-similarity fallbacks
- Embedding generation fails → logged and re-raised, caller handles gracefully
- Circuit breaker OPEN → provider is skipped, fallback provider is tried
- Quota exhausted → provider is skipped, fallback provider is tried

### No New Infrastructure

Embeddings are generated on-the-fly and never persisted. This keeps the infrastructure minimal (no pgvector, no additional databases) and aligns with the zero-budget deployment constraint.

### Raw Embeddings Never Exposed

Public API responses never include raw embedding vectors. Only similarity scores, rankings, and metadata are exposed.

## Quality Gates

- **Ruff**: All checks passed on M88 files
- **MyPy**: No issues found in M88 modules
- **Pytest**: 31/31 M88 tests passed (including 7 new M88.1 failure-mode tests); 384/384 affected regression tests passed
- **TypeScript**: Compilation clean
- **Frontend Build**: Successful (191 modules, 4.52s)

## Known Limitations

1. Embeddings are not cached—each search generates fresh embeddings (acceptable for current scale)
2. Only OpenAI embedding provider implemented; architecture supports additional providers
3. Related stories use a 72-hour cluster window
4. Semantic search is disabled by default (`semantic_search_enabled: false`)
