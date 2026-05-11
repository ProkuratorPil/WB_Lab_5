"""
MinIO object storage service.
Handles file upload/download/delete operations using streaming.
Initializes bucket on startup if it doesn't exist.
"""
import io
import logging
from typing import Optional, BinaryIO
from uuid import UUID, uuid4
from datetime import datetime, timezone

from minio import Minio
from minio.error import S3Error
from app.core.config import settings

logger = logging.getLogger(__name__)

# Allowed MIME types for upload validation
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
    "text/plain",
    "application/zip",
    "application/json",
    "application/octet-stream",
}

# Allowed MIME types for avatars
ALLOWED_AVATAR_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
}

# Max file size (10 MB by default)
MAX_FILE_SIZE = settings.MAX_FILE_SIZE


class MinioService:
    """Service for interacting with MinIO object storage."""

    def __init__(self):
        self._client: Optional[Minio] = None
        self._bucket_name = settings.MINIO_BUCKET
        self._initialized = False

    async def initialize(self):
        """Initialize MinIO client and ensure bucket exists."""
        try:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_USE_SSL,
            )
            # Ensure bucket exists
            if not self._client.bucket_exists(self._bucket_name):
                self._client.make_bucket(self._bucket_name)
                logger.info(f"Created MinIO bucket: {self._bucket_name}")
            else:
                logger.info(f"MinIO bucket already exists: {self._bucket_name}")
            self._initialized = True
            logger.info("MinIO service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MinIO: {e}")
            raise

    def _ensure_initialized(self):
        """Ensure MinIO client is initialized."""
        if not self._initialized or not self._client:
            raise RuntimeError("MinIO service not initialized. Call initialize() first.")

    def _generate_object_key(self, user_id: UUID, original_name: str) -> str:
        """Generate a unique object key for storage."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_id = uuid4().hex[:8]
        # Sanitize the original filename
        safe_name = "".join(c for c in original_name if c.isalnum() or c in "._- ")
        safe_name = safe_name.replace(" ", "_")
        return f"{user_id}/{timestamp}_{unique_id}_{safe_name}"

    def _validate_file_size(self, file_size: int):
        """Validate file size against maximum allowed."""
        if file_size > MAX_FILE_SIZE:
            raise ValueError(
                f"File size exceeds maximum allowed ({MAX_FILE_SIZE // (1024*1024)} MB)"
            )

    def _validate_mime_type(self, mime_type: str, allowed_types: Optional[set] = None):
        """Validate MIME type against allowed types."""
        allowed = allowed_types or ALLOWED_MIME_TYPES
        if mime_type not in allowed:
            raise ValueError(
                f"MIME type '{mime_type}' is not allowed. "
                f"Allowed types: {', '.join(sorted(allowed))}"
            )

    def upload_file(
        self,
        file_stream: BinaryIO,
        file_size: int,
        original_name: str,
        mime_type: str,
        user_id: UUID,
        allowed_types: Optional[set] = None,
    ) -> dict:
        """
        Upload a file to MinIO using streaming.
        Does NOT fully buffer the file in memory.

        Returns:
            dict with keys: object_key, bucket, etag
        """
        self._ensure_initialized()
        self._validate_file_size(file_size)
        self._validate_mime_type(mime_type, allowed_types)

        object_key = self._generate_object_key(user_id, original_name)

        try:
            result = self._client.put_object(
                bucket_name=self._bucket_name,
                object_name=object_key,
                data=file_stream,
                length=file_size,
                content_type=mime_type,
            )
            logger.info(
                f"File uploaded: bucket={self._bucket_name}, "
                f"object_key={object_key}, size={file_size}, "
                f"mime={mime_type}, etag={result.etag}"
            )
            return {
                "object_key": object_key,
                "bucket": self._bucket_name,
                "etag": result.etag,
            }
        except S3Error as e:
            logger.error(f"MinIO upload error: {e}")
            raise

    def get_file_stream(self, object_key: str) -> Optional[BinaryIO]:
        """
        Get a file stream from MinIO for downloading.
        Returns the response object which supports streaming.

        Returns:
            Response object with .data, .stream() methods, or None if not found.
        """
        self._ensure_initialized()
        try:
            response = self._client.get_object(
                bucket_name=self._bucket_name,
                object_name=object_key,
            )
            return response
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"File not found in MinIO: {object_key}")
                return None
            logger.error(f"MinIO get_object error: {e}")
            raise

    def get_file_info(self, object_key: str) -> Optional[dict]:
        """Get file metadata from MinIO."""
        self._ensure_initialized()
        try:
            info = self._client.stat_object(
                bucket_name=self._bucket_name,
                object_name=object_key,
            )
            return {
                "size": info.size,
                "etag": info.etag,
                "content_type": info.content_type,
                "last_modified": info.last_modified,
                "object_key": object_key,
                "bucket": self._bucket_name,
            }
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            logger.error(f"MinIO stat_object error: {e}")
            raise

    def delete_file(self, object_key: str) -> bool:
        """Delete a file from MinIO."""
        self._ensure_initialized()
        try:
            self._client.remove_object(
                bucket_name=self._bucket_name,
                object_name=object_key,
            )
            logger.info(f"File deleted from MinIO: {object_key}")
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(f"File not found in MinIO during delete: {object_key}")
                return False
            logger.error(f"MinIO remove_object error: {e}")
            raise

    def file_exists(self, object_key: str) -> bool:
        """Check if a file exists in MinIO."""
        self._ensure_initialized()
        try:
            self._client.stat_object(
                bucket_name=self._bucket_name,
                object_name=object_key,
            )
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            logger.error(f"MinIO stat_object error: {e}")
            raise


# Global singleton MinIO service
minio_service = MinioService()