"""
Async CRUD operations for MongoDB - UploadedFile document.
Uses Beanie ODM for database operations.
"""
from uuid import UUID
from typing import Optional, List
from datetime import datetime, timezone

from app.models.uploaded_file import UploadedFileDocument


async def get_file_by_id(file_id: UUID) -> Optional[UploadedFileDocument]:
    """Get a single file by ID (excluding deleted)."""
    return await UploadedFileDocument.find_one(
        UploadedFileDocument.id == file_id,
        UploadedFileDocument.deleted_at == None
    )


async def get_user_file_by_id(file_id: UUID, user_id: UUID) -> Optional[UploadedFileDocument]:
    """Get a file by ID and user_id (excluding deleted)."""
    return await UploadedFileDocument.find_one(
        UploadedFileDocument.id == file_id,
        UploadedFileDocument.user_id == user_id,
        UploadedFileDocument.deleted_at == None
    )


async def get_user_files(
    user_id: UUID,
    skip: int = 0,
    limit: int = 10
) -> tuple[list[UploadedFileDocument], int]:
    """Get paginated list of non-deleted files for a user."""
    query = UploadedFileDocument.find(
        UploadedFileDocument.user_id == user_id,
        UploadedFileDocument.deleted_at == None
    )
    total = await query.count()
    files = await query.sort(-UploadedFileDocument.created_at).skip(skip).limit(limit).to_list()
    return files, total


async def create_file(file_data: dict) -> UploadedFileDocument:
    """Create a new uploaded file document."""
    file_doc = UploadedFileDocument(**file_data)
    await file_doc.insert()
    return file_doc


async def soft_delete_file(file_id: UUID) -> bool:
    """Soft delete a file by setting deleted_at."""
    file_doc = await UploadedFileDocument.find_one(UploadedFileDocument.id == file_id)
    if file_doc and file_doc.deleted_at is None:
        file_doc.deleted_at = datetime.now(timezone.utc)
        await file_doc.save()
        return True
    return False