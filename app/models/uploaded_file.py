"""
MongoDB document model for UploadedFile.
Uses Beanie ODM for schema validation and indexing.
"""
from datetime import datetime, timezone
from typing import Optional
from beanie import Document, before_event, Insert, Replace
from pydantic import Field
from uuid import UUID, uuid4


class UploadedFileDocument(Document):
    """MongoDB document for uploaded files with soft delete support.
    
    Stores metadata about files uploaded to MinIO object storage.
    The actual file data lives in MinIO, only metadata is stored here.
    """
    
    id: UUID = Field(default_factory=uuid4, alias="_id")
    user_id: UUID = Field(...)
    original_name: str = Field(...)
    object_key: str = Field(...)
    size: int = Field(...)
    mime_type: str = Field(...)
    bucket: str = Field(...)
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None

    class Settings:
        name = "uploaded_files"
        indexes = [
            [("user_id", 1)],
            [("user_id", 1), ("deleted_at", 1)],
            [("object_key", 1)],
        ]

    @before_event(Insert, Replace)
    def set_timestamps(self):
        """Auto-update timestamps before insert/replace."""
        now = datetime.now(timezone.utc)
        if self.created_at is None:
            self.created_at = now
        self.updated_at = now