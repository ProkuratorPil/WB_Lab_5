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
    """MongoDB document for uploaded files with soft delete support."""
    
    id: UUID = Field(default_factory=uuid4, alias="_id")
    filename: str = Field(...)
    stored_filename: str = Field(...)
    file_path: str = Field(...)
    file_size: int = Field(...)
    mime_type: str = Field(...)
    user_id: UUID = Field(...)
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None

    class Settings:
        name = "uploaded_files"
        indexes = [
            [("user_id", 1)],
            [("user_id", 1), ("deleted_at", 1)],
        ]

    @before_event(Insert, Replace)
    def set_timestamps(self):
        """Auto-update timestamps before insert/replace."""
        now = datetime.now(timezone.utc)
        if self.created_at is None:
            self.created_at = now
        self.updated_at = now
