"""
User API endpoints for the authenticated user.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.schemas.user import UserResponse, UserUpdateRequest
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.exceptions import (
    AuthenticationError,
    DuplicateResourceError,
)
from ai_news_digest.domain.models.user import User
from ai_news_digest.infrastructure.auth.password import hash_password
from ai_news_digest.infrastructure.database.session import get_db_session

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current user's profile",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update the current user's profile",
)
async def update_me(
    request: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    """
    Update the authenticated user's email and/or password.
    """
    container = Container(session)
    user = await container.user_repository.get_by_id(current_user.id)

    if user is None:
        raise AuthenticationError("Authentication required.")

    if request.email is not None and request.email != user.email:
        existing = await container.user_repository.get_by_email(request.email)
        if existing is not None:
            raise DuplicateResourceError("Email already registered.")
        user.email = request.email

    if request.password is not None:
        user.hashed_password = hash_password(request.password)

    updated = await container.user_repository.update(user)

    return UserResponse(
        id=str(updated.id),
        email=updated.email,
        is_active=updated.is_active,
        is_admin=updated.is_admin,
    )


__all__ = ["router"]
