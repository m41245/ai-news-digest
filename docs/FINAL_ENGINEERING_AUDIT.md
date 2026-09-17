# Final Engineering Audit — v1.0 Release Remediation

**Date:** 2026-09-16  
**Auditor:** Kilo (automated)  
**Repository:** C:\Projects\ai-news-digest  
**Branch:** main  
**HEAD:** d66fd24  
**Scope:** v1.0 release remediation — remaining findings from M1–M96 audit

---

## 1. Release Status

**V1.0 READY WITH DOCUMENTED LIMITATIONS**

The three release-critical findings from the previous audit have been remediated. No release blockers remain. Remaining issues are documented limitations or non-blocking defects.

---

## 2. Remediated Findings

### Fixed in This Pass

| ID | Issue | Action |
|----|-------|--------|
| AF-1 | Relationship repository `list_for_entity`, `list_related`, `list_for_entity_with_temporal`, `get_entity_relationship_history`, `count_for_entity`, `count_changes`, `list_activity_events` only queried `subject_entity_type/id` — object-side relationships were invisible | Implemented bidirectional OR queries in all affected repository methods |
| AF-2 | `quality_gate_warning_margin` defaulted to `0.0`, making WARN state mathematically unreachable without explicit config | Changed default to `0.1`; WARN is now reachable by default; explicit config still overrides |
| AF-3 | `or True` bypass in `get_quality_health` (line 302) made baseline drift loading unconditional | Removed bypass; baseline now requires an actual second evaluation run |

### Investigated in This Pass

| ID | Issue | Finding | Classification |
|----|-------|---------|----------------|
| AF-4 | N+1 queries in graph routes | `_build_name_map` uses batched `list_by_ids` (up to 4 queries); not N+1 | No action required |
| AF-5 | N+1 queries in related-story discovery | `RelatedStoryFinder` calls in-memory duplicate detector per candidate; embedding generation is batched; bounded by `story_candidate_limit` | No action required |
| AF-6 | N+1 queries in personalized feed | `get_personalized_feed` called `story_cluster_repository.get_by_id` per cluster ID | **Fixed** — replaced with batch `get_by_ids` |
| AF-7 | N+1 queries in evaluation service | `run_evaluation` calls `list_by_cluster_id` per cluster and `list_evidence_by_claim_id` per claim in background task; bounded by `evaluation_sample_limit=500` | `KNOWN_LIMITATION` — bounded background task; safe to defer |
| AF-8 | Semantic search architecture | Candidates are fetched lexically from DB, then embeddings are generated in batch and similarity is computed in-process. No vector database; no ANN index. This is bounded semantic post-processing, not true vector retrieval | `KNOWN_LIMITATION` — architecture is correct and bounded for v1.0 |
| AF-9 | `_build_graph_name_map` duplication | Identical implementations in `graph.py` and `public.py` | **Fixed** — extracted to shared `api/v1/routes/_graph_utils.py` |

---

## 3. Files Changed

```
 src/ai_news_digest/api/v1/routes/_graph_utils.py       |  69 +
 src/ai_news_digest/api/v1/routes/graph.py              |  70 ++------------------
 src/ai_news_digest/api/v1/routes/public.py             |  64 ++------------------
 .../user_preference/get_personalized_feed.py           |   5 +-
 src/ai_news_digest/core/config.py                      |   2 +-
 .../repositories/relationship_repository.py            |  30 ++++++---
 tests/unit/api/v1/routes/test_graph.py                 |  75 ++++++++++++++++++++++
 .../routes/test_intelligence_evaluation.py             |  29 +++++++++
 .../services/test_quality_gate_service.py              |  28 ++++++++
 .../test_personalized_feed.py                          |  70 ++++++++++++++++++--
 .../repositories/test_relationship_repository.py       | 152 ++++++++++++++++++
 11 files changed, 553 insertions(+), 149 deletions(-)
```

---

## 4. Database

- **Migrations created:** None
- **Migration required:** No
- **Reason:** All fixes are application-layer query, configuration, and refactoring changes. No schema changes.

---

## 5. Tests

### Focused Regression Tests
- `tests/unit/infrastructure/database/repositories/test_relationship_repository.py` — 4 tests, all passed
- `tests/unit/api/v1/routes/test_intelligence_evaluation.py` — 1 test, passed
- `tests/unit/application/services/test_quality_gate_service.py` — 3 tests, all passed
- `tests/unit/api/v1/routes/test_graph.py` — 8 tests, all passed (includes 3 new `build_graph_name_map` tests)
- `tests/unit/application/use_cases/user_preference/test_personalized_feed.py` — 16 tests, all passed (includes 2 new N+1 regression tests)

### Broad Validation
- **Backend unit tests:** 809 passed (excluding 5 pre-existing testcontainers/pytest-asyncio scope errors)
- **Frontend tests:** 40 passed
- **Frontend TypeScript:** Passed
- **Frontend ESLint:** Passed
- **Frontend production build:** Passed
- **Ruff:** Passed on all changed files
- **MyPy:** Passed on all changed files

### Pre-existing Test Failures (not introduced by this pass)
- `tests/unit/api/v1/test_intelligence_workspace.py::TestSavedStoriesAPI::test_save_story` — testcontainers/pytest-asyncio scope mismatch on Windows
- `tests/unit/infrastructure/database/repositories/test_conflict_repository.py` — 5 tests with same scope mismatch

---

## 6. Security

### Verified
- Authorization: Admin RBAC on all admin routes including intelligence evaluation/drift endpoints (unchanged)
- Relationship queries: Bidirectional matching preserves all existing filters, status, limit, and offset semantics
- Quality gate: Default WARN margin is conservative (0.1); explicit configuration still overrides
- Drift endpoint: Baseline requirement enforced; no unconditional bypass remains

### No changes to authentication, authorization, or security boundaries were made in this pass.

---

## 7. Remaining Limitations

| ID | Limitation | Classification |
|----|-----------|----------------|
| KL-7 | Evaluation service `run_evaluation` has N+1 queries for `list_by_cluster_id` and `list_evidence_by_claim_id` in a bounded background task (limits: 500 claims, 200 clusters) | `KNOWN_LIMITATION` |
| KL-8 | Semantic search performs lexical candidate retrieval followed by in-process embedding-based reranking; no vector database or ANN index | `KNOWN_LIMITATION` |
| KL-9 | 5 integration-style tests fail on Windows due to pytest-asyncio + testcontainers scope mismatch | Pre-existing environmental issue |

---

## 8. Future Enhancements

- Batch `list_by_cluster_ids` and `list_evidence_by_claim_ids` repository methods to eliminate N+1 in evaluation service
- Vector database integration for true semantic retrieval at scale
- JWT refresh tokens and revocation blacklist
- Password special-character requirement
- Real-time notification delivery

---

## 9. Git

- **Branch:** main
- **HEAD:** d66fd24
- **origin/main:** d66fd24
- **Working tree:** Clean after commit

---

## 10. Final Recommendation

**V1.0 READY WITH DOCUMENTED LIMITATIONS**

All three release-critical findings from the previous audit have been remediated:
1. Bidirectional relationship queries now surface all relevant graph connections
2. Quality-gate WARN state is reachable by default with a conservative 0.1 margin
3. Drift endpoint baseline requirement is enforced without bypass

Two safe optimizations were implemented:
- Personalized feed now loads story clusters in a single batch query
- Duplicated `_build_graph_name_map` was extracted to a shared module

Two limitations are documented as acceptable for v1.0:
- Evaluation service N+1 is bounded by existing limits and runs in a background task
- Semantic search uses bounded lexical+semantic reranking rather than true vector retrieval

No release blockers remain.
