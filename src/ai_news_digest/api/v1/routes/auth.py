"""
Authentication API endpoints.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
)
from ai_news_digest.api.v1.schemas.user import UserResponse
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.exceptions import AuthenticationError
from ai_news_digest.domain.models.user import User
from ai_news_digest.infrastructure.auth.jwt import create_access_token
from ai_news_digest.infrastructure.auth.password import hash_password, verify_password
from ai_news_digest.infrastructure.database.session import get_db_session

_DUMMY_HASH = hash_password("DummyHash1234567890")

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login and obtain access token",
)
async def login(
    request: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LoginResponse:
    """
    Authenticate a user and return a JWT access token.
    """
    container = Container(session)
    user = await container.user_repository.get_by_email(request.username)

    if user is None:
        verify_password(request.password, _DUMMY_HASH)
        raise AuthenticationError("Invalid email or password.")

    if not verify_password(request.password, user.hashed_password):
        raise AuthenticationError("Invalid email or password.")

    if not user.is_active:
        raise AuthenticationError("Inactive user.")

    settings = get_settings()
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.jwt_expiration_minutes),
    )

    return LoginResponse(access_token=access_token)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    request: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    """
    Register a new user account.
    """
    container = Container(session)
    existing = await container.user_repository.get_by_email(request.email)

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    hashed_password = hash_password(request.password)
    user = User.create(
        email=request.email,
        hashed_password=hashed_password,
        is_active=True,
    )

    created = await container.user_repository.create(user)

    return UserResponse(
        id=str(created.id),
        email=created.email,
        is_active=created.is_active,
        is_admin=created.is_admin,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout",
)
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict[str, str]:
    """
    Logout the current user.

    The API uses stateless JWT access tokens without server-side sessions or a
    revocation blacklist, so logout is a client-side concern: the client should
    discard the token. This endpoint exists for API completeness and to give
    clients a clear, authenticated endpoint to call on sign-out.
    """
    return {"message": "Logged out successfully."}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """
    Return the profile of the currently authenticated user.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )


__all__ = ["router"]
