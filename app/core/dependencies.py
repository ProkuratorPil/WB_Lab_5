"""
Dependencies for authentication and authorization with MongoDB.
"""
from fastapi import Depends, HTTPException, status, Cookie, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from uuid import UUID

from app.core.jwt import verify_access, verify_refresh
from app.core.security import hash_token
from app.core.cache import cache_service
from app.models.user import UserDocument
from app.models.token import TokenDocument, TokenType
from app.crud.token_crud import get_token_by_hash


# Schemes for token extraction
security = HTTPBearer(auto_error=False)


def _check_access_jti_in_redis(user_id: UUID, jti: str) -> bool:
    """
    Check if Access Token JTI exists in Redis.
    If key is missing - token is revoked or expired.
    """
    key = f"wp:auth:user:{user_id}:access:{jti}"
    value = cache_service.get(key)
    return value is not None


async def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(default=None, alias="access_token"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserDocument:
    """
    Dependency to get the current authenticated user.
    Checks Access Token from Cookie or Authorization header.
    Checks JTI in Redis for instant revocation.
    """
    token = None

    # Try from Cookie
    if access_token:
        token = access_token
    # Try from Authorization header
    elif credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate JWT
    payload = verify_access(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истёкший токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = UUID(payload["sub"])
    jti = payload.get("jti")

    # Check JTI in Redis (instant revocation)
    if jti and not _check_access_jti_in_redis(user_id, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен был отозван",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check that token is not revoked in DB
    token_hash_val = hash_token(token)
    db_token = await get_token_by_hash(token_hash_val)
    if db_token and db_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен был отозван",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from MongoDB
    user = await UserDocument.find_one(
        UserDocument.id == user_id,
        UserDocument.deleted_at == None,
        UserDocument.is_active == True
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    request: Request,
    access_token: Optional[str] = Cookie(default=None, alias="access_token"),
) -> Optional[UserDocument]:
    """
    Optional version - returns user or None.
    Used for endpoints accessible to everyone.
    """
    if not access_token:
        return None

    try:
        payload = verify_access(access_token)
        if not payload:
            return None

        user_id = UUID(payload["sub"])
        jti = payload.get("jti")

        if jti and not _check_access_jti_in_redis(user_id, jti):
            return None

        user = await UserDocument.find_one(
            UserDocument.id == user_id,
            UserDocument.deleted_at == None,
            UserDocument.is_active == True
        )

        return user
    except Exception:
        return None


async def get_refresh_token(
    refresh_token: Optional[str] = Cookie(default=None, alias="refresh_token"),
) -> str:
    """Dependency to get Refresh Token from Cookie."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh токен отсутствует",
        )
    return refresh_token


async def validate_refresh_token(
    request: Request,
    refresh_token: str = Depends(get_refresh_token),
) -> tuple[UserDocument, str]:
    """
    Validate Refresh Token and return the user.
    Checks token revocation in DB.
    """
    user_id = verify_refresh(refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истёкший refresh токен",
        )

    # Check token in DB
    token_hash_val = hash_token(refresh_token)
    db_token = await get_token_by_hash(token_hash_val)

    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не найден в системе",
        )

    if db_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен был отозван",
        )

    # Get user from MongoDB
    user = await UserDocument.find_one(
        UserDocument.id == user_id,
        UserDocument.deleted_at == None,
        UserDocument.is_active == True
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    return user, refresh_token


def get_client_ip(request: Request) -> str:
    """Get client IP address."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Get client User-Agent."""
    return request.headers.get("User-Agent", "unknown")