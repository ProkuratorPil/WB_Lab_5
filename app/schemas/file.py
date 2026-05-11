from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class FileResponse(BaseModel):
    """Response schema for file metadata (object_key and bucket are hidden from client)."""
    id: UUID
    original_name: str
    size: int
    mime_type: str
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=100)


class PaginatedFileResponse(BaseModel):
    data: list[FileResponse]
    meta: dict