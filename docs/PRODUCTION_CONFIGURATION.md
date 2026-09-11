# Production Configuration Reference

This document describes all configuration values required to run AI News Digest in production.

## Configuration Sources

Configuration is loaded in the following order (highest precedence first):

1. Environment variables
2. `.env.prod.local` file (via `docker compose --env-file`)
3. `.env` file (ignored in production)
4. Default values in code

**Never commit `.env`, `.env.prod.local`, or any file containing secrets to version control.**

---

## Required Production Variables

### Application

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Must be `production` | `production` |
| `DEBUG` | Must be `false` in production | `false` |
| `HOST` | Host to bind ASGI server to (Render requires `0.0.0.0`) | `0.0.0.0` |
| `PORT` | Port for ASGI server (Render provides this automatically) | `8000` |
| `JWT_SECRET_KEY` | Secure random key (min 32 chars) | `openssl rand -hex 32` output |
| `CORS_ORIGINS` | JSON array of allowed origins | `["https://ai-news-digest-doo.pages.dev"]` |

### Database

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_DB` | Database name | `ai_news_digest` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `<secure-password>` |
| `DATABASE_URL` | Async PostgreSQL URL. Use `postgresql+asyncpg://` or the standard `postgresql://` format from Neon/Render; the shared application/Alembic helper translates it at connection time. | `postgresql+asyncpg://postgres:postgres@postgres:5432/ai_news_digest` |

### PostgreSQL Driver

The application and Alembic migrations use `asyncpg` as the PostgreSQL driver.

If `DATABASE_URL` is provided in the standard `postgresql://` format (e.g., from Neon or Render), the application and Alembic migrations normalize it to `postgresql+asyncpg://` through the same shared helper. `sslmode=require`, `verify-ca`, and `verify-full` are consumed and translated to asyncpg's secure `ssl=True` connect argument; `sslmode=disable` becomes `ssl=False`, while `allow` and `prefer` use asyncpg's native SSL negotiation. Neon URLs may also include `channel_binding=require`. asyncpg 0.31 does not expose that libpq option, so it is consumed and TLS is forced, but the driver cannot enforce the additional SCRAM channel-binding requirement. `application_name` is translated to asyncpg `server_settings`; query parameters accepted by asyncpg or SQLAlchemy's asyncpg dialect are preserved. Unsupported TLS certificate-file parameters fail closed so certificate verification is not silently weakened. The URL and matching `connect_args` are applied consistently to both the application engine and migrations.

Do not install or configure `psycopg2` — it is not a dependency and will conflict with the async architecture.

### Redis

| Variable | Description | Example |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL (use `rediss://` for TLS/Upstash) | `rediss://default:token@upstash-host:6379` |
| `CELERY_BROKER_URL` | Celery broker URL (use `rediss://` for TLS/Upstash) | `rediss://default:token@upstash-host:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery result backend (use `rediss://` for TLS/Upstash) | `rediss://default:token@upstash-host:6379/2` |

Authentication is embedded in the Redis URL (username:password@host). No separate `REDIS_PASSWORD` variable is required.

#### Redis TLS and URL Format

For Upstash and other TLS-requiring Redis providers, use the `rediss://` scheme:

```text
rediss://default:password@upstash-host:6379/0
```

**Important distinctions:**

- `REDIS_URL` must be a **Redis connection URL** (e.g. `rediss://default:password@host:6379/0`), not a shell command.
- A `redis-cli --tls -u rediss://...` string is a CLI invocation and is **not** a valid Redis URL. Passing such a string as `REDIS_URL` causes URL parsing to fail.
- The application uses `redis-py` (`redis.asyncio.ConnectionPool.from_url`) to create the connection pool. When the URL scheme is `rediss://`, the library automatically configures an SSL/TLS-wrapped connection (`SSLConnection`). No manual `ssl=True` flag is needed in application code.
- Do **not** downgrade to `redis://` for TLS-requiring providers. Plaintext connections will be rejected by the server with `Connection closed by server`.
- Do **not** disable certificate verification in application code to make the connection work. If TLS handshake issues occur, verify that the URL hostname matches the server certificate and that outbound port 6379 (or the provider's TLS port) is reachable from Render.

##### Startup Diagnostics

When the application starts, it logs a safe, credential-free summary of the Redis configuration:

```text
Redis configuration: scheme=rediss host=upstash-host.example port=6379 db=0 tls=true credentials_present=true
```

This log line confirms:
- The URL scheme (`rediss` vs `redis`)
- The target hostname and port
- The database index
- Whether TLS is expected
- Whether credentials are present

If `scheme=redis` appears in production logs instead of `scheme=rediss`, the `REDIS_URL` environment variable is using plaintext and must be corrected.

##### Troubleshooting "Connection closed by server"

If `/health/ready` reports `"cache": "unavailable"` with `Connection closed by server`:

1. **Check the startup log** for the `Redis configuration` line. Confirm `scheme=rediss` and `tls=true`.
2. **Verify the Render environment variable** `REDIS_URL` starts with `rediss://`, not `redis://`.
3. **Verify the Upstash hostname** in `REDIS_URL` matches the endpoint shown in the Upstash Console.
4. **Verify the password/token** is correct. An incorrect password causes an authentication error, not `Connection closed by server`, but double-check if the token was regenerated.
5. **Verify outbound connectivity** from Render to the Upstash hostname on port 6379. Render free-tier outbound networking should reach Upstash, but corporate firewalls or VPC configurations can interfere.
6. **Verify Celery** is also using `rediss://` for `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`. Kombu's Redis transport automatically enables SSL when the scheme is `rediss://`.

If the diagnostics show the correct `rediss://` scheme and the error persists, the failure is most likely network/DNS connectivity (D) or an Upstash server-side restriction (F). Contact Upstash support with the exact timestamp and hostname to investigate server-side connection logs.

##### redis-py version and TLS behavior

The application uses `redis-py` 5.3.1. In this version:

- `ConnectionPool.from_url('rediss://...')` automatically selects `SSLConnection`
- `SSLConnection` creates an `ssl.SSLContext` with `ssl.create_default_context()`, which:
  - Verifies the server certificate against system CA certificates (`cert_reqs=CERT_REQUIRED`)
  - Does **not** verify the hostname by default (`check_hostname=False`)
- No explicit `ssl=True` parameter is needed in application code when using `from_url()`
- Query parameters in the URL (e.g. `?socket_timeout=10`) are parsed and passed to the connection

##### Celery Redis Transport

Celery uses Kombu's Redis transport. When the broker URL uses the `rediss://` scheme:

- Kombu sets `ssl={'ssl_cert_reqs': ssl.CERT_NONE}` by default for backward compatibility
- The connection class is set to `redis.SSLConnection`
- **Certificate verification is disabled** (`CERT_NONE`) in the Kombu transport path

This is a known limitation of Kombu's Redis transport. The application's direct Redis usage (via `redis-py`) maintains proper certificate verification. If certificate verification is required for Celery connections, set `ssl_cert_reqs=required` via Kombu transport options.

---

## Optional Variables

### AI Providers

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | (empty) |
| `OPENAI_ENABLED` | Enable OpenAI provider | `false` |
| `OPENAI_MODEL` | OpenAI model name | `gpt-4o-mini` |
| `OPENAI_PRIORITY` | Provider priority (lower = higher) | `1` |
| `OPENAI_TIMEOUT` | Request timeout in seconds | `30` |
| `OPENAI_MAX_RETRIES` | Max retry attempts | `3` |
| `ANTHROPIC_API_KEY` | Anthropic API key | (empty) |
| `ANTHROPIC_ENABLED` | Enable Anthropic provider | `false` |
| `ANTHROPIC_MODEL` | Anthropic model name | `claude-3-5-haiku-20241022` |
| `ANTHROPIC_PRIORITY` | Provider priority | `2` |
| `ANTHROPIC_TIMEOUT` | Request timeout in seconds | `30` |
| `ANTHROPIC_MAX_RETRIES` | Max retry attempts | `3` |
| `DEFAULT_LLM_PROVIDER` | Default AI provider | `openai` |

### Email / SMTP

Email is optional. Set `EMAIL_ENABLED=true` and provide the SMTP settings below to enable email delivery.

| Variable | Description | Default |
|----------|-------------|---------|
| `EMAIL_ENABLED` | Enable email notification delivery | `false` |
| `EMAIL_PROVIDER` | Provider: `smtp`, `console`, `test` | `console` |
| `EMAIL_DEVELOPMENT_MODE` | Force console email sender even in non-development environments | `true` |
| `EMAIL_BASE_URL` | Base URL used in email links | (empty) |
| `EMAIL_FROM_ADDRESS` | Sender email address | `noreply@ai-news-digest.com` |
| `EMAIL_FROM_NAME` | Sender display name | `AI News Digest` |
| `EMAIL_REPLY_TO` | Reply-to address | (empty) |
| `EMAIL_MAX_RETRIES` | Max retry attempts for transient failures | `3` |
| `EMAIL_RETRY_DELAY` | Base retry delay in seconds | `60` |
| `EMAIL_BATCH_SIZE` | Max emails per batch | `50` |
| `EMAIL_RATE_LIMIT` | Max emails per rate limit window | `100` |
| `EMAIL_TIMEOUT` | Timeout per delivery operation | `30` |
| `SMTP_HOST` | SMTP server hostname | `localhost` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username | (empty) |
| `SMTP_PASSWORD` | SMTP password | (empty) |

### Application Tuning

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `RATE_LIMIT` | Max requests per window | `60` |
| `RATE_LIMIT_WINDOW` | Rate limit window in seconds | `60` |
| `RSS_REQUEST_TIMEOUT` | RSS fetch timeout | `20` |
| `RSS_MAX_ARTICLES_PER_FEED` | Max articles per feed | `50` |
| `DIGEST_TIMEZONE` | Digest scheduling timezone | `UTC` |
| `DIGEST_SCHEDULE_HOUR` | Hour for daily digest (0-23) | `8` |
| `DIGEST_SCHEDULE_MINUTE` | Minute for daily digest (0-59) | `0` |
| `METRICS_ALLOWED_IPS` | Comma-separated list of IPs allowed to access `/metrics` | (empty = admin auth only) |
| `EMAIL_DEVELOPMENT_MODE` | Force console email sender even in non-development environments | `true` |

### Monitoring

| Variable | Description | Default |
|----------|-------------|---------|
| `METRICS_ALLOWED_IPS` | Optional IP allow-list for `/metrics` endpoint (defense-in-depth) | (empty) |
| `SENTRY_DSN` | Sentry DSN for error tracking | (empty) |

---

## Development-Only Variables

These variables are used in development and testing environments. They should NOT be set in production.

| Variable | Description |
|----------|-------------|
| `APP_NAME` | Application display name |
| `APP_VERSION` | Application version |
| `API_PREFIX` | API route prefix (`/api/v1`) |
| `AI_MAX_CONTENT_LENGTH` | Max AI content length |
| `AI_SUMMARIZATION_MAX_TOKENS` | Max summarization tokens |
| `AI_SUMMARIZATION_TEMPERATURE` | Summarization temperature |
| `AI_CATEGORIZATION_MAX_TOKENS` | Max categorization tokens |
| `AI_CATEGORIZATION_TEMPERATURE` | Categorization temperature |
| `AI_RETRY_MAX_ATTEMPTS` | AI retry attempts |
| `AI_RETRY_BASE_DELAY` | AI retry base delay |
| `AI_RETRY_MAX_DELAY` | AI retry max delay |

---

## Feature-Specific Credentials

### Email Delivery

Required only if email delivery is enabled:
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `EMAIL_FROM`
- `EMAIL_RECIPIENTS`

### AI Processing

Required only if AI processing is enabled:
- `OPENAI_API_KEY` (when `OPENAI_ENABLED=true`)
- `ANTHROPIC_API_KEY` (when `ANTHROPIC_ENABLED=true`)

---

## Secret Management

In production, inject secrets via one of the following methods:

1. **Docker Compose env-file** (simple, single-host):
   ```bash
   docker compose --env-file .env.prod.local up -d
   ```

2. **Environment variables** (container orchestration):
   ```bash
   export POSTGRES_PASSWORD="secure-value"
   docker compose up -d
   ```

3. **Docker secrets** (Docker Swarm):
   ```bash
   echo "secure-value" | docker secret create postgres_password -
   ```

4. **External secrets manager** (HashiCorp Vault, AWS Secrets Manager, etc.)

**Never store production secrets in the repository or in Docker images.**

---

## Validation

The application validates `JWT_SECRET_KEY` on startup:
- Must be at least 32 characters
- Must not match known weak defaults

If validation fails, the application will refuse to start.

### Production Configuration Validator

A standalone validation script is provided at `scripts/validate_production_config.py`. Run it before starting the application in production:

```bash
python scripts/validate_production_config.py
```

The validator checks:
- `ENVIRONMENT=production`
- `DEBUG=false`
- `JWT_SECRET_KEY` is set and secure (min 32 chars, not a placeholder)
- `DATABASE_URL` is set and points to PostgreSQL
- `REDIS_URL` is set and points to Redis
- `CELERY_BROKER_URL` is set
- `CELERY_RESULT_BACKEND` is set
- `CORS_ORIGINS` is set to real production origins (not empty)
- `EMAIL_DEVELOPMENT_MODE=false`
- `EMAIL_PROVIDER=smtp` when email is enabled
- `EMAIL_BASE_URL` is set to the public application URL when email is enabled
- `OPENAI_API_KEY` is set when `OPENAI_ENABLED=true`
- `ANTHROPIC_API_KEY` is set when `ANTHROPIC_ENABLED=true`
- `SMTP_HOST` is set when `EMAIL_PROVIDER=smtp` and email is enabled

### Application-Level Production Validators

In addition to the startup script, the application validates the following at Settings load time:
- `EMAIL_DEVELOPMENT_MODE` must be `false` in production
- `EMAIL_PROVIDER` must be `smtp` in production when email is enabled
- `EMAIL_BASE_URL` must be set in production when email is enabled
- `OPENAI_API_KEY` must be set when `OPENAI_ENABLED=true` in production
- `ANTHROPIC_API_KEY` must be set when `ANTHROPIC_ENABLED=true` in production
- `SMTP_HOST` must be set when `EMAIL_PROVIDER=smtp` in production and email is enabled

If any validator fails, the application will refuse to start.

## JWT Token Lifecycle

This application uses stateless JWT access tokens without refresh tokens or a server-side revocation blacklist. The security tradeoffs are:

- **Access token lifetime**: Default 60 minutes (configurable via `JWT_EXPIRATION_MINUTES`)
- **No refresh tokens**: Users must re-authenticate after token expiration
- **No revocation blacklist**: A compromised token remains valid until its expiration time
- **Logout is client-side**: The `/auth/logout` endpoint returns a success message but does not invalidate the token server-side

**Operational implications:**
- If a token needs to be invalidated early (e.g., user compromise), change `JWT_SECRET_KEY` to invalidate all active sessions
- For production deployments requiring token revocation, implement a Redis-backed blacklist and add `jti` claims to tokens
- Keep `JWT_SECRET_KEY` consistent across rolling restarts to avoid invalidating active sessions

## Email Development Mode

The `EMAIL_DEVELOPMENT_MODE` setting controls email delivery behavior:
- `true` (default): All emails are printed to console logs instead of being sent via SMTP
- `false`: Emails are sent via the configured SMTP provider

**In production, always set `EMAIL_DEVELOPMENT_MODE=false`** to ensure emails are actually delivered to recipients.
