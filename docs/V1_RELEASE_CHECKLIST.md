# AI News Digest V1 — Release Checklist

Practical checklist for the solo maintainer. Mark each item only after verifying it.
Do not commit, push, merge, or deploy without explicit owner authorization.

Repository: `C:\Users\raj1m\.local\share\kilo\worktree-pool\ai-news-digest-ec7a9d72f95b\feat-free-provider-groq`
Branch: `feat/free-provider-groq`
HEAD: `81963930ea4d2613f5df0630e830e5ffe8578419`

---

## Pre-flight (never skip)

- [ ] Working tree inspected; all pre-existing modifications and untracked files preserved
- [ ] No secrets, connection strings, or tokens in any file, log, or report
- [ ] No production database, secrets, or configuration accessed
- [ ] No commits, pushes, merges, or deployments performed in this session

---

## 1. Code correctness

- [ ] Batch runner enforces `--batch-size` on every pipeline stage (summarize, categorize, analyze, cluster)
- [ ] Runner uses existing application services (no duplicated business logic)
- [ ] No unintended ingestion; no accidental AI calls; no Redis broker required for direct execution
- [ ] No destructive database operations; explicit transaction boundaries and rollback
- [ ] Single-instance overlap lock present and functioning
- [ ] Failed stage halts pipeline; failed article rolled back without corrupting others
- [ ] Repeated execution is idempotent (no duplicate clusters/digests)
- [ ] AI-enabled task path still routes through the use case and persists results

## 2. Testing

- [ ] Batch runner unit tests pass (13)
- [ ] Related task/lifecycle unit tests pass (47)
- [ ] Isolated PostgreSQL integration tests pass (20) against real PostgreSQL via testcontainers
- [ ] No test connects to production or mutates staging data

## 3. Quality gates

- [ ] Ruff lint clean on all changed/new files
- [ ] Ruff format clean on all changed/new files
- [ ] Mypy clean on `run_deterministic_batch.py`, `process.py`, `cluster.py`, `trend.py`
- [ ] Docker build succeeds
- [ ] `docker compose config` valid for all compose files
- [ ] Entrypoint shell syntax valid (`bash -n entrypoint.sh`)

## 4. Staging (read-only only — no mutations)

- [ ] Staging service reachable (`https://ai-news-digest-staging.onrender.com`)
- [ ] `/health/live` returns 200
- [ ] `/health/ready` returns 200
- [ ] `/api/v1/public/sources` returns 200 with expected schema
- [ ] `/api/v1/public/articles?limit=5` returns 200 with expected schema
- [ ] `/api/v1/public/digests` returns 200
- [ ] `/api/v1/public/story-ranking/top-story` returns 200
- [ ] `/api/v1/public/story-clusters` returns 200
- [ ] `/api/v1/public/trends` returns 200
- [ ] No existing staging article mutated
- [ ] No ingestion or processing triggered against staging

> Staging was unreachable (HTTP 503 / connection timeout) during this session. These checks could not be completed and require owner investigation via Render service events/logs.

## 5. Operating workflow (free, one-shot model)

- [ ] Dry-run command documented and verified: `python scripts/scheduled/run_deterministic_batch.py --batch-size N --dry-run`
- [ ] Bounded batch command documented: `python scripts/scheduled/run_deterministic_batch.py --batch-size N`
- [ ] Full deterministic pipeline command documented (all 7 stages in order)
- [ ] Selective stages / skip-stages documented
- [ ] Progress inspection via structured logging documented
- [ ] Failure recovery documented (re-run is idempotent; skip failed stage with `--skip-stages`)
- [ ] Exit codes documented: 0 success, 1 failure, 2 another instance running
- [ ] No automatically recurring workflow created
- [ ] No new Render service created

## 6. Security and reliability

- [ ] No full source article reproduced; summaries original and concise
- [ ] Attribution and source links preserved
- [ ] Missing content not fabricated; scores/confidence not invented
- [ ] Deterministic processing does not imply AI verification
- [ ] AI disabled (`AI_ENABLED=false`); email disabled; production schedules disabled
- [ ] CORS, auth, rate limiting, input validation reviewed for the public API
- [ ] SQL injection protection via parameterized queries/ORM

## 7. Cost

- [ ] Operating model remains ₹0 (Render free tier, Neon free tier, Valkey/Redis cache only)
- [ ] No paid services created or upgraded
- [ ] No new external paid dependencies
- [ ] Free services not assumed durable; fallback documented

## 8. Owner approvals still required

- [ ] Staging live validation (service reachability investigation via Render)
- [ ] Staging processing test (separate explicit approval specifying exact command, DB target, batch limit, selection criteria, expected mutations, backup/recovery, rollback, expected API results, AI-not-called verification, production-untouched verification)
- [ ] Commit / push / merge / deploy (each separately authorized)

## 9. Release sequence

1. Owner reviews this checklist and the readiness report
2. Owner investigates staging 503 (Render access) and confirms service reachability
3. Owner performs read-only staging API checks
4. Owner reviews and approves the staging processing test plan (separate approval)
5. (If approved) Run bounded staging processing test against a copy/subset with backup and rollback
6. Verify API reflects processed data; confirm no AI calls and production untouched
7. Owner authorizes commit, push, and deploy

---

**Verdict (this session):** `CODE READY — LIVE OPERATION NOT VERIFIED` — code is complete and tested against isolated PostgreSQL, but live staging operation could not be verified because the staging service is unreachable.
