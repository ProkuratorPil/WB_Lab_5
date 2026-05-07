"""
MongoDB document model for Token.
Uses Beanie ODM for schema validation and indexing.
"""
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from beanie import Document, before_event
from pydantic import Field
from uuid import UUID, uuid4


class TokenType(str, Enum):
    access = "access"
    refresh = "refresh"


class TokenDocument(Document):
    """MongoDB document for JWT tokens with revocation support."""
    
    id: UUID = Field(default_factory=uuid4, alias="_id")
    user_id: UUID = Field(...)
    token_type: TokenType = Field(...)
    token_hash: str = Field(...)
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    is_revoked: bool = False
    expires_at: datetime = Field(...)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "tokens"
        indexes = [
            [("token_hash", 1)],
            [("user_id", 1)],
            [("user_id", 1), ("is_revoked", 1)],
        ]

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_revoked and not self.is_expired


class RefreshTokenDocument(Document):
    """Separate collection for refresh tokens with longer TTL."""
    
    id: UUID = Field(default_factory=uuid4, alias="_id")
    user_id: UUID = Field(...)
    token_hash: str = Field(...)
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    is_revoked: bool = False
    expires_at: datetime = Field(...)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "refresh_tokens"
        indexes = [
            [("token_hash", 1)],
            [("user_id", 1)],
        ]