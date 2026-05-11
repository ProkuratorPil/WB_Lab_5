"""
Async service for file management with MinIO and MongoDB.
Handles file upload to MinIO with streaming and stores metadata in MongoDB.
"""
from uuid import UUID
from typing import Optional, BinaryIO
from datetime import datetime, timezone

from app.models.uploaded_file import UploadedFileDocument
from app.schemas.file import FileResponse
from app.crud import file_crud
from app.services.minio_service import minio_service, ALLOWED_MIME_TYPES, ALLOWED_AVATAR_MIME_TYPES
from app.core.cache import cache_service


class FileService:
    """Service for file operations with MinIO storage and Redis caching."""

    async def upload_file(
        self,
        file_stream: BinaryIO,
        file_size: int,
        original_name: str,
        mime_type: str,
        user_id: UUID,
        is_avatar: bool = False,
    ) -> UploadedFileDocument:
        """
        Upload a file to MinIO and store metadata in MongoDB.
        Uses streaming - does not buffer entire file in memory.
        
        Args:
            file_stream: File-like object for streaming
            file_size: Size of the file in bytes
            original_name: Original filename
            mime_type: MIME type of the file
            user_id: UUID of the uploading user
            is_avatar: If True, validates against avatar MIME types
            
        Returns:
            UploadedFileDocument with file metadata
        """
        allowed_types = ALLOWED_AVATAR_MIME_TYPES if is_avatar else ALLOWED_MIME_TYPES

        # Upload to MinIO using streaming
        upload_result = minio_service.upload_file(
            file_stream=file_stream,
            file_size=file_size,
            original_name=original_name,
            mime_type=mime_type,
            user_id=user_id,
            allowed_types=allowed_types,
        )

        # Store metadata in MongoDB
        file_data = {
            "user_id": user_id,
            "original_name": original_name,
            "object_key": upload_result["object_key"],
            "size": file_size,
            "mime_type": mime_type,
            "bucket": upload_result["bucket"],
        }

        file_doc = await file_crud.create_file(file_data)
        
        # Invalidate file list cache for this user
        cache_service.delete_by_pattern(f"wp:files:list:{user_id}:*")
        
        return file_doc

    async def get_file_metadata(self, file_id: UUID, user_id: UUID) -> Optional[UploadedFileDocument]:
        """
        Get file metadata by ID.
        First checks Redis cache, then MongoDB.
        Verifies user ownership.
        """
        # Check cache first
        cache_key = f"wp:files:{file_id}:meta"
        cached = cache_service.get(cache_key)
        if cached:
            return UploadedFileDocument(**cached) if not isinstance(cached, UploadedFileDocument) else cached

        # Get from DB with ownership check
        file_doc = await file_crud.get_user_file_by_id(file_id, user_id)
        if file_doc:
            # Cache metadata
            cache_service.set(cache_key, file_doc.model_dump(mode="json"), ttl=300)
        
        return file_doc

    async def get_file_by_id(self, file_id: UUID) -> Optional[UploadedFileDocument]:
        """Get file metadata by ID without ownership check."""
        return await file_crud.get_file_by_id(file_id)

    async def get_user_files(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 10
    ) -> tuple[list[UploadedFileDocument], int]:
        """Get paginated list of user's files with caching."""
        offset = (page - 1) * limit
        files, total = await file_crud.get_user_files(user_id, skip=offset, limit=limit)
        return files, total

    async def delete_file(self, file_id: UUID, user_id: UUID) -> bool:
        """
        Delete a file: hard delete from MinIO, soft delete in MongoDB.
        Verifies user ownership.
        """
        file_doc = await self.get_file_metadata(file_id, user_id)
        if not file_doc:
            return False

        # Hard delete from MinIO
        try:
            minio_service.delete_file(file_doc.object_key)
        except Exception as e:
            # Log but continue - the DB record will be soft deleted
            import logging
            logging.getLogger(__name__).warning(
                f"MinIO delete failed for {file_doc.object_key}: {e}"
            )

        # Soft delete in MongoDB
        result = await file_crud.soft_delete_file(file_id)
        
        if result:
            # Invalidate caches
            cache_key = f"wp:files:{file_id}:meta"
            cache_service.delete(cache_key)
            cache_service.delete_by_pattern(f"wp:files:list:{user_id}:*")

        return result

    async def download_file_stream(self, file_id: UUID, user_id: UUID):
        """
        Get file stream for download.
        Returns (stream, metadata) tuple or (None, None) if not found/unauthorized.
        """
        file_doc = await self.get_file_metadata(file_id, user_id)
        if not file_doc:
            return None, None

        stream = minio_service.get_file_stream(file_doc.object_key)
        if not stream:
            return None, None

        return stream, file_doc