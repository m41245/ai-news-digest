from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import HTMLResponse
from jinja2 import Template
from sqlalchemy import select

from ai_news_digest.api.v1.dependencies.auth import get_current_admin_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.common import (
    DEFAULT_PAGE_LIMIT,
    MAX_OFFSET,
    MAX_PAGE_LIMIT,
    PaginatedResponse,
)
from ai_news_digest.api.v1.schemas.user import (
    AdminUserResponse,
    AdminUserUpdateRequest,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.config import settings
from ai_news_digest.core.exceptions import (
    DuplicateResourceError,
    ResourceNotFoundError,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.user import User
from ai_news_digest.infrastructure.auth.password import hash_password
from ai_news_digest.infrastructure.database.models.article_model import ArticleModel
from ai_news_digest.infrastructure.database.models.digest_delivery_model import (
    DigestDeliveryModel,
)
from ai_news_digest.infrastructure.database.models.digest_model import DigestModel
from ai_news_digest.workers.celery_app import celery_app

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get("/users", response_model=PaginatedResponse[AdminUserResponse], summary="List users")
async def list_users(
    container: Annotated[Container, Depends(get_container)],
    _: Annotated[User, Depends(get_current_admin_user)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
) -> PaginatedResponse[AdminUserResponse]:
    """Return registered users with pagination (admin only)."""
    users = await container.user_repository.list_all(limit=limit, offset=offset)
    total = await container.user_repository.count()

    return PaginatedResponse(
        items=[
            AdminUserResponse(
                id=str(user.id),
                email=user.email,
                is_active=user.is_active,
                is_admin=user.is_admin,
                created_at=user.created_at,
            )
            for user in users
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Get a user",
)
async def get_user(
    user_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    _: Annotated[User, Depends(get_current_admin_user)],
) -> AdminUserResponse:
    """Return a single user by ID (admin only)."""
    user = await container.user_repository.get_by_id(user_id)

    if user is None:
        raise ResourceNotFoundError(f"User {user_id} not found.")

    return AdminUserResponse(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
    )


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Update a user",
)
async def update_user(
    user_id: UUID,
    request: AdminUserUpdateRequest,
    container: Annotated[Container, Depends(get_container)],
    _: Annotated[User, Depends(get_current_admin_user)],
) -> AdminUserResponse:
    """Update a user's status, role, email or password (admin only)."""
    user = await container.user_repository.get_by_id(user_id)

    if user is None:
        raise ResourceNotFoundError(f"User {user_id} not found.")

    if request.email is not None and request.email != user.email:
        existing = await container.user_repository.get_by_email(request.email)
        if existing is not None:
            raise DuplicateResourceError("Email already registered.")
        user.email = request.email

    if request.is_active is not None:
        user.is_active = request.is_active

    if request.is_admin is not None:
        user.is_admin = request.is_admin

    if request.password is not None:
        user.hashed_password = hash_password(request.password)

    updated = await container.user_repository.update(user)

    return AdminUserResponse(
        id=str(updated.id),
        email=updated.email,
        is_active=updated.is_active,
        is_admin=updated.is_admin,
        created_at=updated.created_at,
    )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a user",
)
async def delete_user(
    user_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    _: Annotated[User, Depends(get_current_admin_user)],
) -> None:
    """Delete a user by ID (admin only)."""
    user = await container.user_repository.get_by_id(user_id)

    if user is None:
        raise ResourceNotFoundError(f"User {user_id} not found.")

    await container.user_repository.delete(user_id)


@router.get("/stats")
async def get_system_stats(
    container: Annotated[Container, Depends(get_container)],
    _: Annotated[User, Depends(get_current_admin_user)],
) -> dict[str, object]:
    """Return system statistics."""
    articles = await container.article_repository.count()
    sources = await container.source_repository.list_all()
    digests = await container.digest_repository.count()

    return {
        "articles": articles,
        "sources": len(sources),
        "digests": digests,
        "status": "ok",
    }


@router.post(
    "/ingestion/run",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_ingestion(
    _: Annotated[User, Depends(get_current_admin_user)],
) -> dict[str, str]:
    """Trigger the ingestion pipeline via Celery."""
    from ai_news_digest.workers.tasks.ingest import fetch_all_sources

    task = fetch_all_sources.delay()

    return {
        "message": "Ingestion triggered.",
        "task_id": task.id,
    }


@router.post(
    "/digest/run",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_digest_generation(
    _: Annotated[User, Depends(get_current_admin_user)],
) -> dict[str, str]:
    """Trigger digest generation via Celery."""
    from ai_news_digest.workers.tasks.digest import generate_daily_digest

    task = generate_daily_digest.delay()

    return {
        "message": "Digest generation triggered.",
        "task_id": task.id,
    }


@router.post(
    "/cleanup",
    status_code=status.HTTP_202_ACCEPTED,
)
async def cleanup_database(
    _: Annotated[User, Depends(get_current_admin_user)],
) -> dict[str, str]:
    """Trigger cleanup tasks via Celery."""
    from ai_news_digest.workers.tasks.cleanup import cleanup_old_articles

    task = cleanup_old_articles.delay(days=30)

    return {
        "message": "Cleanup triggered.",
        "task_id": task.id,
    }


@router.get("/health")
async def admin_health(
    _: Annotated[User, Depends(get_current_admin_user)],
) -> dict[str, str]:
    """Administrative health endpoint."""
    return {
        "status": "healthy",
        "service": "admin",
    }


@router.get("/workers/health")
async def worker_health(
    _: Annotated[User, Depends(get_current_admin_user)],
) -> dict[str, object]:
    """Return Celery worker health and connectivity status."""
    try:
        ping_result = celery_app.control.ping(timeout=5)
        worker_count = len(ping_result)
        workers_online = worker_count > 0 and all(
            response.get("ok") == "pong" for result in ping_result for response in result.values()
        )

        return {
            "workers_online": worker_count > 0,
            "workers_responded": worker_count,
            "workers": [
                {
                    "hostname": hostname,
                    "status": response.get("ok", "unknown"),
                }
                for result in ping_result
                for hostname, response in result.items()
            ],
            "broker_connected": worker_count > 0,
            "status": "healthy" if workers_online else "degraded",
        }
    except Exception as exc:
        return {
            "workers_online": False,
            "workers_responded": 0,
            "broker_connected": False,
            "error": str(exc),
            "status": "unhealthy",
        }


@router.get("/pipeline/status")
async def pipeline_status(
    container: Annotated[Container, Depends(get_container)],
    _: Annotated[User, Depends(get_current_admin_user)],
) -> dict[str, object]:
    """Return operational pipeline status derived from existing data."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import func

    session = container.session
    article_model = ArticleModel
    digest_model = DigestModel
    delivery_model = DigestDeliveryModel

    now = datetime.now(UTC)
    recent_threshold = timedelta(hours=26)
    stale_threshold = timedelta(days=2)

    def is_recent(timestamp: datetime | None) -> bool:
        if timestamp is None:
            return False
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        delta: timedelta = now - timestamp
        return delta <= recent_threshold

    def is_stale(timestamp: datetime | None) -> bool:
        if timestamp is None:
            return True
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        delta: timedelta = now - timestamp
        return delta > stale_threshold

    warnings: list[str] = []

    last_ingestion = (
        await session.execute(select(func.max(article_model.fetched_at)))
    ).scalar_one_or_none()
    last_processing = (
        await session.execute(
            select(func.max(article_model.updated_at)).where(
                article_model.status.in_(
                    [
                        ArticleStatus.SUMMARIZED.value,
                        ArticleStatus.CATEGORIZED.value,
                        ArticleStatus.READY.value,
                    ]
                )
            )
        )
    ).scalar_one_or_none()
    last_digest = (
        await session.execute(select(func.max(digest_model.generated_at)))
    ).scalar_one_or_none()
    last_delivery = (
        await session.execute(select(func.max(delivery_model.sent_at)))
    ).scalar_one_or_none()

    new_articles = (
        await session.execute(
            select(func.count(article_model.id)).where(article_model.status == "new")
        )
    ).scalar_one_or_none() or 0
    failed_deliveries = (
        await session.execute(
            select(func.count(delivery_model.id)).where(delivery_model.status == "failed")
        )
    ).scalar_one_or_none() or 0

    status = "ok"
    if not is_recent(last_ingestion):
        status = "degraded"
        if is_stale(last_ingestion):
            warnings.append("ingestion_stale")
    if not is_recent(last_digest):
        status = "degraded"
        if is_stale(last_digest):
            warnings.append("digest_stale")
    if is_stale(last_processing) and last_processing is not None:
        warnings.append("processing_stale")
    if is_stale(last_delivery) and last_delivery is not None:
        warnings.append("delivery_stale")
    if new_articles > 0:
        warnings.append("pending_articles")
    if failed_deliveries > 0:
        warnings.append("failed_deliveries")

    return {
        "status": status,
        "warnings": warnings,
        "ingestion": {
            "last_attempt": last_ingestion.isoformat() if last_ingestion else None,
            "last_success": last_ingestion.isoformat() if last_ingestion else None,
        },
        "processing": {
            "last_attempt": last_processing.isoformat() if last_processing else None,
            "last_success": last_processing.isoformat() if last_processing else None,
        },
        "digest": {
            "last_attempt": last_digest.isoformat() if last_digest else None,
            "last_generated": last_digest.isoformat() if last_digest else None,
        },
        "delivery": {
            "last_attempt": last_delivery.isoformat() if last_delivery else None,
            "last_sent": last_delivery.isoformat() if last_delivery else None,
        },
        "counts": {
            "new_articles": new_articles,
            "failed_deliveries": failed_deliveries,
        },
    }


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    _: Annotated[User, Depends(get_current_admin_user)],
) -> dict[str, object]:
    """Return the status and result of a Celery task by ID."""
    result = celery_app.AsyncResult(task_id)

    response: dict[str, object] = {
        "task_id": task_id,
        "state": result.state,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "failed": result.failed() if result.ready() else None,
    }

    if result.ready():
        if result.failed():
            exc_type = type(result.result).__name__ if result.result else "Exception"
            response["error"] = {
                "type": exc_type,
                "message": "Task failed. Check worker logs for details.",
            }
        else:
            response["result"] = result.result

    if result.state == "PROGRESS":
        response["progress"] = result.info

    return response


_DASHBOARD_TEMPLATE = Template(
    """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI News Digest &mdash; Admin Dashboard</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; color: #111; }
    h1 { margin-bottom: .25rem; }
    h2 { margin-top: 2rem; }
    table { border-collapse: collapse; width: 100%; margin-top: .5rem; }
    th, td { border: 1px solid #ccc; padding: .4rem .6rem; text-align: left; }
    th { background: #f4f4f4; }
    .stat { display: inline-block; margin-right: 1.5rem; }
    .stat b { font-size: 1.4rem; }
    a { color: #0a58ca; }
  </style>
</head>
<body>
  <h1>AI News Digest &mdash; Admin Dashboard</h1>
  <p>Server-rendered administrative overview. Requires administrator authentication.</p>

  <h2>System Status</h2>
  <div class="stat"><span>Articles</span><br><b>{{ stats.articles }}</b></div>
  <div class="stat"><span>Sources</span><br><b>{{ sources|length }}</b></div>
  <div class="stat"><span>Digests</span><br><b>{{ stats.digests }}</b></div>
  <div class="stat"><span>Users</span><br><b>{{ users|length }}</b></div>

  <h2>Users</h2>
  <table>
    <tr><th>Email</th><th>Active</th><th>Admin</th></tr>
    {% for u in users %}
    <tr><td>{{ u.email }}</td><td>{{ u.is_active }}</td><td>{{ u.is_admin }}</td></tr>
    {% endfor %}
  </table>

  <h2>Sources</h2>
  <table>
    <tr><th>Name</th><th>Feed URL</th><th>Active</th></tr>
    {% for s in sources %}
    <tr><td>{{ s.name }}</td><td>{{ s.feed_url }}</td><td>{{ s.is_active }}</td></tr>
    {% endfor %}
  </table>

  <h2>API</h2>
  {% if settings.environment != "production" %}
  <p>Interactive API documentation: <a href="/docs">Swagger UI</a> &middot;
     <a href="/api/v1/openapi.json">OpenAPI</a></p>
  {% endif %}
</body>
</html>
""",
    autoescape=True,
)


@router.get(
    "/dashboard",
    response_class=HTMLResponse,
    summary="Admin dashboard",
)
async def admin_dashboard(
    container: Annotated[Container, Depends(get_container)],
    _: Annotated[User, Depends(get_current_admin_user)],
) -> str:
    """
    Server-rendered administrative dashboard.

    Provides visibility into users, sources, articles and digests. Access is
    restricted to administrators; sensitive fields such as password hashes are
    never rendered.
    """
    articles = await container.article_repository.count()
    digests = await container.digest_repository.count()
    users = await container.user_repository.list_all(limit=100)
    sources = await container.source_repository.list_all(limit=100)

    return _DASHBOARD_TEMPLATE.render(
        stats={
            "articles": articles,
            "digests": digests,
        },
        users=users,
        sources=sources,
        settings=settings,
    )


__all__ = ["router"]
