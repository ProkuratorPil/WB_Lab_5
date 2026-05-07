"""
Async CRUD operations for MongoDB - User document.
Uses Beanie ODM for database operations.
"""
from uuid import UUID
from typing import Optional, Tuple, List
from datetime import datetime, timezone

from app.models.user import UserDocument
from app.schemas.user import UserCreate, UserUpdate


async def get_users(skip: int = 0, limit: int = 10) -> Tuple[List[UserDocument], int]:
    """
    Get paginated list of non-deleted users.
    Returns (users, total_count).
    """
    query = UserDocument.find(UserDocument.deleted_at == None)
    total = await query.count()
    users = await query.sort(-UserDocument.created_at).skip(skip).limit(limit).to_list()
    return users, total


async def get_user_by_id(user_id: UUID) -> Optional[UserDocument]:
    """Get a single user by ID (excluding deleted)."""
    return await UserDocument.find_one(
        UserDocument.id == user_id,
        UserDocument.deleted_at == None
    )


async def get_user_by_username(username: str) -> Optional[UserDocument]:
    """Get a user by username (including deleted)."""
    return await UserDocument.find_one(UserDocument.username == username)


async def get_user_by_email(email: str) -> Optional[UserDocument]:
    """Get a user by email (including deleted)."""
    return await UserDocument.find_one(UserDocument.email == email)


async def get_user_by_yandex_id(yandex_id: str) -> Optional[UserDocument]:
    """Get a user by Yandex OAuth ID."""
    return await UserDocument.find_one(UserDocument.yandex_id == yandex_id)


async def get_user_by_vk_id(vk_id: str) -> Optional[UserDocument]:
    """Get a user by VK OAuth ID."""
    return await UserDocument.find_one(UserDocument.vk_id == vk_id)


async def create_user(user_data: dict) -> UserDocument:
    """Create a new user document."""
    user = UserDocument(**user_data)
    await user.insert()
    return user


async def update_user(user_id: UUID, update_data: dict) -> Optional[UserDocument]:
    """Update a user document partially."""
    user = await get_user_by_id(user_id)
    if not user:
        return None
    
    for key, value in update_data.items():
        if value is not None:
            setattr(user, key, value)
    
    user.updated_at = datetime.now(timezone.utc)
    await user.save()
    return user


async def soft_delete_user(user_id: UUID) -> bool:
    """Soft delete a user by setting deleted_at."""
    user = await UserDocument.find_one(UserDocument.id == user_id)
    if user and user.deleted_at is None:
        user.deleted_at = datetime.now(timezone.utc)
        await user.save()
        return True
    return False


async def get_user_by_id_raw(user_id: UUID) -> Optional[UserDocument]:
    """Get a user by ID without soft-delete filter."""
    return await UserDocument.find_one(UserDocument.id == user_id)