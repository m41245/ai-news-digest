# AI News Digest V1 — Staging Operational Runbook

**Release branch:** `release/v1-deterministic-pipeline`
**Base:** latest verified `origin/main`
**Release HEAD:** `d95017110f87d5f58c2431694b376e3e01b34590`

---

## 1. Architecture overview

| Component | Technology | Cost | Status |
|-----------|-----------|------|--------|
| Web application | FastAPI + Uvicorn (Docker) | ₹0 (Render free tier) | Not deployed to staging (staging unreachable) |
| Cache | Redis / Valkey (Upstash free 25 MB) | ₹0 | Not verified live |
| Database | PostgreSQL (Neon free tier) | ₹0 | Not verified live |
| Processing runner | Python script (this runbook) | ₹0 | Bounded, one-shot |
| Celery worker | Celery + Redis broker | Not on free tier | Not operational |
| Celery Beat | Celery beat scheduler | Not on free tier | Not operational |
| AI providers | OpenAI, Anthropic, Gemini, Groq, xAI | Disabled | AI_ENABLED=false |
| Email | SMTP / console | Disabled | EMAIL_ENABLED=false |

**Zero-cost processing architecture:** A bounded, explicitly invoked batch runner (`scripts/scheduled/run_deterministic_batch.py`) executes the deterministic pipeline without requiring a persistent Celery worker, Beat scheduler, or Redis-backed durable queue. The existing Celery infrastructure remains as a documented optional alternative for paid-tier deployments.

---

## 2. How to run deterministic processing manually

```bash
# From the repository root
python scripts/scheduled/run_deterministic_batch.py --batch-size 100
```

This runs all pipeline stages in order:
1. Summarize: NEW → SUMMARIZED
2. Categorize: SUMMARIZED → CATEGORIZED
3. Analyze: CATEGORIZED/SUMMARIZED → ANALYZED
4. Cluster: unclustered processed articles → story clusters
5. Rank: story clusters → ranked scores + top story
6. Trends: detect trends from clusters/activity
7. Digest: generate daily digest from eligible articles

---

## 3. How to run a dry run

```bash
python scripts/scheduled/run_deterministic_batch.py --batch-size 100 --dry-run
```

The dry run reports what would be processed without mutating the database. Use this before any production run to verify expected batch sizes.

---

## 4. How to process a bounded batch

```bash
# Process at most 50 articles per stage
python scripts/scheduled/run_deterministic_batch.py --batch-size 50

# Process only specific stages
python scripts/scheduled/run_deterministic_batch.py --stages summarize,categorize --batch-size 50

# Skip expensive stages
python scripts/scheduled/run_deterministic_batch.py --skip-stages trends,digest --batch-size 100
```

`--batch-size` bounds only the summarize, categorize, analyze, and cluster
stages. Rank, trends, and digest operate on the full eligible collection
and are not limited by `--batch-size`.

---

## 5. How to inspect task progress

Progress is reported via structured logging. Check the application logs for entries like:

```
[info] Stage complete stage=summarize processed=50 failed=0 status=completed
[info] Stage complete stage=categorize processed=50 failed=0 status=completed
[info] Deterministic batch runner finished elapsed_seconds=12.34 stages_run=7 total_processed=350 total_failed=0
```

---

## 6. How to recover from a failed batch

The pipeline is idempotent and stage-ordered:

1. **Identify the failed stage** from the logs (look for `status=failed`).
2. **Fix the underlying issue** (e.g., database connectivity, missing configuration).
3. **Re-run the pipeline** — already-processed articles are skipped automatically:
   ```bash
   python scripts/scheduled/run_deterministic_batch.py --batch-size 100
   ```
4. **If a specific stage keeps failing**, skip it and continue with later stages:
   ```bash
   python scripts/scheduled/run_deterministic_batch.py --skip-stages <failed_stage> --batch-size 100
   ```

Transaction safety: each stage uses explicit commit/rollback boundaries. Failed processing rolls back safely without corrupting article lifecycle state.

---

## 7. How to avoid duplicate processing

- All pipeline stages are idempotent — articles already in the target status are skipped
- The summarizer checks `article.status != ArticleStatus.NEW` before processing
- The categorizer checks `article.status != ArticleStatus.SUMMARIZED` before processing
- The analyzer checks `article.status == ArticleStatus.ANALYZED` before processing
- The clusterer checks `article.cluster_id is not None` before processing
- Digest generation checks for existing today's digest before creating a new one

Never run multiple instances of the batch runner concurrently against the same database. The runner now uses a single-instance lock (stored in the system temp directory): if a live instance already holds the lock, a second invocation exits with code 2. Stale locks from dead processes are reclaimed automatically.

---

## 8. How to verify generated digests

```bash
# Read-only checks against the staging API
curl https://ai-news-digest-staging.onrender.com/api/v1/public/digests
curl https://ai-news-digest-staging.onrender.com/api/v1/public/story-ranking/top-story
curl https://ai-news-digest-staging.onrender.com/api/v1/public/story-clusters
curl https://ai-news-digest-staging.onrender.com/api/v1/public/trends
```

Verify that:
- Digests have non-zero `article_count` when eligible articles exist
- Empty state is correctly represented when no eligible stories exist
- Top story returns appropriate empty response when no clusters exist

---

## 9. How to monitor staging health

```bash
curl https://ai-news-digest-staging.onrender.com/health/live
curl https://ai-news-digest-staging.onrender.com/health/ready
```

Expected responses:
- `/health/live` → `alive`
- `/health/ready` → `ready`

If the service returns 503, the Render free-tier instance may have spun down. Wait and retry.

---

## 10. What must remain disabled

| Feature | Setting | Reason |
|---------|---------|--------|
| AI | `AI_ENABLED=false` | No AI provider budget on ₹0 infrastructure |
| Email | `EMAIL_ENABLED=false` | No email delivery budget |
| Production scheduling | `ENABLE_PRODUCTION_SCHEDULE=false` | Production protection |
| Celery worker on Render | Not deployed | Render free tier doesn't support workers |
| Celery Beat on Render | Not deployed | Render free tier doesn't support workers |

---

## 11. What is not supported on the free infrastructure

- Persistent Celery worker (Render free tier)
- Celery Beat scheduler (Render free tier)
- Redis-backed durable queue (staging Redis is cache-only, 25 MB, no persistence)
- AI model inference (no provider budget)
- Email delivery (no provider budget)
- Production deployment (separately protected)

---

## 12. How to safely promote a future release

1. Verify staging is reachable: `/health/live` and `/health/ready` return 200
2. Run read-only API checks against all public endpoints
3. Run the deterministic batch runner with `--dry-run` first
4. Run the batch runner with a small `--batch-size` (e.g., 10) with owner approval
5. Verify API responses reflect processed data
6. Do not commit, push, merge, or deploy without explicit owner authorization

---

## 13. Component distinction

| Component | Responsibility | How to run |
|-----------|---------------|------------|
| Web application | Serves API, health checks, public routes | Render web service / `uvicorn ai_news_digest.main:app` |
| Cache | Redis store for rate limiting, session cache | Upstash Redis / `REDIS_URL` |
| One-shot processing runner | Bounded deterministic pipeline execution | `python scripts/scheduled/run_deterministic_batch.py` |
| Optional Celery worker | Background task processing (paid tier) | `celery -A ai_news_digest.workers.celery_app worker` |
| Optional Celery Beat | Periodic task scheduling (paid tier) | `celery -A ai_news_digest.workers.celery_app beat` |
| Optional AI provider | LLM-based summarization/categorization/analysis | `AI_ENABLED=true` + provider API key (not on free tier) |

---

## 14. Emergency contacts and escalation

- Repository: `m41245/ai-news-digest`
- Branch: `release/v1-deterministic-pipeline`
- Staging URL: `https://ai-news-digest-staging.onrender.com`
- Staging Render service: `ai-news-digest-staging`

All changes must be reviewed by the owner before commit, push, or deploy.
