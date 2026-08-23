from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import HTMLResponse
from jinja2 import Template

from ai_news_digest.api.v1.dependencies.auth import get_current_admin_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.user import (
    AdminUserResponse,
    AdminUserUpdateRequest,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.exceptions import (
    DuplicateResourceError,
    ResourceNotFoundError,
)
from ai_news_digest.domain.models.user import User
from ai_news_digest.infrastructure.auth.password import hash_password

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get("/users", response_model=list[AdminUserResponse], summary="List users")
async def list_users(
    container: Annotated[Container, Depends(get_container)],
    _: Annotated[User, Depends(get_current_admin_user)],
) -> list[AdminUserResponse]:
    """Return all registered users (admin only)."""
    users = await container.user_repository.list_all()

    return [
        AdminUserResponse(
            id=str(user.id),
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
        )
        for user in users
    ]


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
    articles = await container.article_repository.list_recent(limit=1)
    sources = await container.source_repository.list_all()
    digests = await container.digest_repository.list_recent(limit=1)

    return {
        "articles": len(articles),
        "sources": len(sources),
        "digests": len(digests),
        "status": "ok",
    }


@router.post(
    "/ingestion/run",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_ingestion(
    container: Annotated[Container, Depends(get_container)],
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
    container: Annotated[Container, Depends(get_container)],
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
    container: Annotated[Container, Depends(get_container)],
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
  <p>Interactive API documentation: <a href="/docs">Swagger UI</a> &middot;
     <a href="/api/v1/openapi.json">OpenAPI</a></p>
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
    articles = await container.article_repository.list_recent(limit=1)
    digests = await container.digest_repository.list_recent(limit=1)
    users = await container.user_repository.list_all()
    sources = await container.source_repository.list_all()

    return _DASHBOARD_TEMPLATE.render(
        stats={
            "articles": len(articles),
            "digests": len(digests),
        },
        users=users,
        sources=sources,
    )


__all__ = ["router"]
