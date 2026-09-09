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
| `JWT_SECRET_KEY` | Secure random key (min 32 chars) | `openssl rand -hex 32` output |
| `CORS_ORIGINS` | JSON array of allowed origins | `["https://app.example.com"]` |

### Database

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_DB` | Database name | `ai_news_digest` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `<secure-password>` |
| `DATABASE_URL` | Async PostgreSQL URL | `postgresql+asyncpg://postgres:postgres@postgres:5432/ai_news_digest` |

### Redis

| Variable | Description | Example |
|----------|-------------|---------|
| `REDIS_PASSWORD` | Redis authentication password | `<secure-password>` |
| `REDIS_URL` | Redis connection URL | `redis://:redis@redis:6379/0` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://:redis@redis:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://:redis@redis:6379/2` |

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

| Variable | Description | Default |
|----------|-------------|---------|
| `SMTP_HOST` | SMTP server hostname | `localhost` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username | (empty) |
| `SMTP_PASSWORD` | SMTP password | (empty) |
| `EMAIL_FROM` | Sender email address | `noreply@ai-news-digest.com` |
| `EMAIL_RECIPIENTS` | JSON array of recipient emails | `[]` |

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
- `REDIS_PASSWORD` is set (required in production)
- `CELERY_BROKER_URL` is set
- `CELERY_RESULT_BACKEND` is set
- `CORS_ORIGINS` is set to real production origins (not empty)
- `EMAIL_DEVELOPMENT_MODE=false`
- `EMAIL_PROVIDER=smtp` when email is enabled
- `EMAIL_BASE_URL` is set to the public application URL
- `OPENAI_API_KEY` is set when `OPENAI_ENABLED=true`
- `ANTHROPIC_API_KEY` is set when `ANTHROPIC_ENABLED=true`
- `SMTP_HOST` is set when `EMAIL_PROVIDER=smtp`

### Application-Level Production Validators

In addition to the startup script, the application validates the following at Settings load time:
- `EMAIL_DEVELOPMENT_MODE` must be `false` in production
- `EMAIL_PROVIDER` must be `smtp` in production when email is enabled
- `EMAIL_BASE_URL` must be set in production
- `OPENAI_API_KEY` must be set when `OPENAI_ENABLED=true` in production
- `ANTHROPIC_API_KEY` must be set when `ANTHROPIC_ENABLED=true` in production
- `SMTP_HOST` must be set when `EMAIL_PROVIDER=smtp` in production

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
