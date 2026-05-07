"""
Async service for file management with MongoDB.
Uses Beanie ODM for database operations.
"""
from uuid import UUID
from typing import Optional, Tuple, List
from datetime import datetime, timezone

from app.models.uploaded_file import UploadedFileDocument
from app.schemas.file import FileCreate, FileUpdate, PaginationParams
from app.crud import file_crud


class FileService:
    """Service for file operations."""

    def __init__(self):
        pass  # No db session needed - Beanie handles connection

    async def create(self, data: FileCreate) -> UploadedFileDocument:
        """Create a new file record."""
        return await file_crud.create_file(data.model_dump())

    async def get_by_id(self, file_id: UUID) -> Optional[UploadedFileDocument]:
        """Get file by ID."""
        return await file_crud.get_file_by_id(file_id)

    async def get_all_active(
        self, 
        pagination: PaginationParams, 
        user_id_filter: Optional[UUID] = None
    ) -> Tuple[List[UploadedFileDocument], int, int]:
        """
        Get paginated list of active files.
        Returns (files, total, total_pages).
        """
        offset = (pagination.page - 1) * pagination.limit
        files, total = await file_crud.get_files(
            user_id_filter=user_id_filter, 
            skip=offset, 
            limit=pagination.limit
        )
        total_pages = (total + pagination.limit - 1) // pagination.limit
        return files, total, total_pages

    async def update(self, file_id: UUID, data: FileUpdate) -> Optional[UploadedFileDocument]:
        """Update a file record."""
        return await file_crud.update_file(file_id, data.model_dump(exclude_unset=True))

    async def delete(self, file_id: UUID) -> bool:
        """Soft delete a file."""
        return await file_crud.soft_delete_file(file_id)