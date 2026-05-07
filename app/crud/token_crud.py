"""
Async CRUD operations for MongoDB - Token document.
Uses Beanie ODM for database operations.
"""
from uuid import UUID
from typing import Optional
from datetime import datetime, timezone

from app.models.token import TokenDocument, TokenType


async def create_token(
    user_id: UUID,
    token: str,
    token_type: TokenType,
    user_agent: str = None,
    ip_address: str = None,
    expires_at: datetime = None
) -> TokenDocument:
    """
    Create a new token document.
    Token is hashed before saving.
    """
    from app.core.security import hash_token
    token_hash = hash_token(token)
    
    db_token = TokenDocument(
        user_id=user_id,
        token_type=token_type,
        token_hash=token_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=expires_at
    )
    
    await db_token.insert()
    return db_token


async def get_token_by_hash(token_hash: str) -> Optional[TokenDocument]:
    """Get a token by its hash."""
    return await TokenDocument.find_one(TokenDocument.token_hash == token_hash)


async def get_user_tokens(user_id: UUID) -> list[TokenDocument]:
    """Get all active (non-revoked, non-expired) tokens for a user."""
    tokens = await TokenDocument.find(
        TokenDocument.user_id == user_id,
        TokenDocument.is_revoked == False,
        TokenDocument.expires_at > datetime.now(timezone.utc)
    ).to_list()
    return tokens


async def revoke_token(token_id: UUID) -> bool:
    """Revoke a token by ID."""
    token = await TokenDocument.find_one(TokenDocument.id == token_id)
    if token:
        token.is_revoked = True
        await token.save()
        return True
    return False


async def revoke_all_user_tokens(user_id: UUID) -> int:
    """Revoke all tokens for a user. Returns count of revoked tokens."""
    result = await TokenDocument.find(
        TokenDocument.user_id == user_id,
        TokenDocument.is_revoked == False
    ).update({"$set": {"is_revoked": True}})
    return result.modified_count


async def cleanup_expired_tokens() -> int:
    """Delete expired tokens from the database."""
    result = await TokenDocument.find(
        TokenDocument.expires_at < datetime.now(timezone.utc)
    ).delete()
    return result.deleted_count