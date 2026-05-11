"""
Async service for user management with MongoDB.
Uses Beanie ODM for database operations and Redis for caching.
"""
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, Tuple, List
from fastapi import HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel

from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, 
    ProfileUpdate, ProfileResponse, PaginationParams
)
from app.core.cache import cache_service
from app.core.config import settings
from app.models.user import UserDocument
from app.crud import book as user_crud

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class UserService:
    """Service for user operations with caching support."""

    def __init__(self):
        pass  # No db session needed - Beanie handles connection

    async def create(self, data: UserCreate) -> UserResponse:
        # Check unique username
        existing = await user_crud.get_user_by_username(data.username)
        if existing and existing.deleted_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким username уже существует"
            )

        # Check unique email
        existing = await user_crud.get_user_by_email(data.email)
        if existing and existing.deleted_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )

        hashed_password = pwd_context.hash(data.password)
        user_dict = data.model_dump()
        user_dict['hashed_password'] = hashed_password
        del user_dict['password']

        user = await user_crud.create_user(user_dict)
        
        # Invalidate cache
        cache_service.delete_by_pattern("wp:users:list:*")
        
        return UserResponse.model_validate(user)

    async def get_by_id(self, user_id: UUID) -> Optional[UserDocument]:
        """Internal method without caching (for DB operations)."""
        return await user_crud.get_user_by_id(user_id)

    async def get_by_id_cached(self, user_id: UUID) -> Optional[UserResponse]:
        """Public method with caching (for API responses)."""
        cache_key = f"wp:users:detail:{user_id}"
        cached = cache_service.get(cache_key)
        if cached:
            return UserResponse(**cached)

        user = await self.get_by_id(user_id)
        if user:
            user_data = UserResponse.model_validate(user).model_dump(mode="json")
            cache_service.set(cache_key, user_data, ttl=settings.CACHE_TTL_DEFAULT)
            return UserResponse.model_validate(user)
        return None

    async def get_all_active(self, pagination: PaginationParams) -> Tuple[List, int]:
        cache_key = f"wp:users:list:page:{pagination.page}:limit:{pagination.limit}"
        cached = cache_service.get(cache_key)
        if cached:
            return [UserResponse(**u) for u in cached["users"]], cached["total"]

        offset = (pagination.page - 1) * pagination.limit
        users, total = await user_crud.get_users(skip=offset, limit=pagination.limit)

        # Cache serialized data
        users_data = [UserResponse.model_validate(u).model_dump(mode="json") for u in users]
        cache_service.set(cache_key, {"users": users_data, "total": total}, ttl=settings.CACHE_TTL_DEFAULT)
        
        return [UserResponse.model_validate(u) for u in users], total

    async def update(self, user_id: UUID, data: UserUpdate, partial: bool = False) -> Optional[UserResponse]:
        user = await self.get_by_id(user_id)
        if not user:
            return None

        update_data = data.model_dump(exclude_unset=partial)
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if 'password' in update_data and update_data['password'] is not None:
            update_data['hashed_password'] = pwd_context.hash(update_data.pop('password'))

        updated_user = await user_crud.update_user(user_id, update_data)
        if not updated_user:
            return None

        user_response = UserResponse.model_validate(updated_user)
        
        # Invalidate cache
        cache_service.delete_by_pattern("wp:users:list:*")
        cache_service.delete(f"wp:users:detail:{user_id}")
        cache_service.delete(f"wp:users:profile:{user_id}")
        
        return user_response

    async def delete(self, user_id: UUID) -> bool:
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        result = await user_crud.soft_delete_user(user_id)
        
        if result:
            # Invalidate cache
            cache_service.delete_by_pattern("wp:users:list:*")
            cache_service.delete(f"wp:users:detail:{user_id}")
            cache_service.delete(f"wp:users:profile:{user_id}")
        
        return result

    async def get_profile(self, user_id: UUID) -> ProfileResponse:
        """Get user profile with caching."""
        cache_key = f"wp:users:profile:{user_id}"
        cached = cache_service.get(cache_key)
        if cached:
            return ProfileResponse(**cached)

        user = await self.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        profile = ProfileResponse.model_validate(user)
        cache_service.set(cache_key, profile.model_dump(mode="json"), ttl=settings.CACHE_TTL_DEFAULT)
        return profile

    async def update_profile(self, user_id: UUID, data: ProfileUpdate) -> ProfileResponse:
        """Update user profile (including avatar)."""
        user = await self.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        update_data = data.model_dump(exclude_unset=True)
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if update_data:
            updated_user = await user_crud.update_user(user_id, update_data)
            if not updated_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Не удалось обновить профиль"
                )
            
            # Invalidate profile and user caches
            cache_service.delete(f"wp:users:profile:{user_id}")
            cache_service.delete(f"wp:users:detail:{user_id}")
            cache_service.delete_by_pattern("wp:users:list:*")

            return ProfileResponse.model_validate(updated_user)

        # No updates - return current profile
        return ProfileResponse.model_validate(user)