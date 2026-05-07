"""
MongoDB document model for User.
Uses Beanie ODM for schema validation and indexing.
"""
from datetime import datetime, timezone
from typing import Optional
from beanie import Document, before_event, Insert, Replace
from pydantic import Field
from uuid import UUID, uuid4


class UserDocument(Document):
    """MongoDB document for users with soft delete support."""
    
    id: UUID = Field(default_factory=uuid4, alias="_id")
    username: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., max_length=100)
    hashed_password: Optional[str] = None
    password_salt: Optional[str] = None
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    
    # OAuth providers
    yandex_id: Optional[str] = None
    vk_id: Optional[str] = None
    
    # Account status
    is_active: bool = True
    is_verified: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None

    class Settings:
        name = "users"
        indexes = [
            [("username", 1)],
            [("email", 1)],
            [("yandex_id", 1)],
            [("vk_id", 1)],
        ]

    @property
    def is_oauth_user(self) -> bool:
        """Check if user registered via OAuth."""
        return self.hashed_password is None and (self.yandex_id is not None or self.vk_id is not None)

    @before_event(Insert, Replace)
    def set_timestamps(self):
        """Auto-update timestamps before insert/replace."""
        now = datetime.now(timezone.utc)
        if self.created_at is None:
            self.created_at = now
        self.updated_at = now