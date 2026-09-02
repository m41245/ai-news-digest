from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.exceptions import AuthenticationError, AuthorizationError
from ai_news_digest.domain.models.user import User
from ai_news_digest.infrastructure.auth.jwt import decode_access_token
from ai_news_digest.infrastructure.database.session import get_db_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """
    Dependency that extracts and validates the current user from a JWT token.
    """
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise AuthenticationError("Invalid authentication credentials.") from exc

    user_id = payload.sub

    if user_id is None:
        raise AuthenticationError("Invalid authentication credentials.")

    container = Container(session)
    user = await container.user_repository.get_by_id(user_id)

    if user is None:
        raise AuthenticationError("Invalid authentication credentials.")

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency that ensures the current user is active.
    """
    if not current_user.is_active:
        raise AuthenticationError("Inactive user.")

    return current_user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Dependency that ensures the current user is an admin.
    """
    if not current_user.is_admin:
        raise AuthorizationError("Admin access required.")

    return current_user
