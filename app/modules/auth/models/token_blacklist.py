"""
Token blacklist model for JWT token management.
"""

from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.orm import Session

from app.core.models.base import BaseModel


class TokenBlacklist(BaseModel):
    """Model for tracking blacklisted/revoked JWT tokens."""

    __tablename__ = "token_blacklist"

    # Token information
    jti = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="JWT ID (unique token identifier)"
    )

    token_type = Column(
        String(20),
        nullable=False,
        comment="Type of token (access, refresh)"
    )

    # Token metadata
    user_id = Column(String(255), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revocation_reason = Column(String(100), nullable=True)

    # Optional token content for debugging (hashed)
    token_hash = Column(Text, nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index('idx_token_blacklist_jti_type', 'jti', 'token_type'),
        Index('idx_token_blacklist_expires_at', 'expires_at'),
        Index('idx_token_blacklist_user_revoked', 'user_id', 'revoked_at'),
    )

    def __repr__(self) -> str:
        return f"<TokenBlacklist(jti={self.jti}, type={self.token_type}, revoked_at={self.revoked_at})>"

    @classmethod
    def is_token_blacklisted(cls, db: Session, jti: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            db: Database session
            jti: JWT ID to check

        Returns:
            True if token is blacklisted
        """
        return db.query(cls).filter(cls.jti == jti).first() is not None

    @classmethod
    def blacklist_token(
        cls,
        db: Session,
        jti: str,
        token_type: str,
        expires_at: datetime,
        user_id: str | None = None,
        reason: str | None = None,
        token_hash: str | None = None
    ) -> "TokenBlacklist":
        """
        Add a token to the blacklist.

        Args:
            db: Database session
            jti: JWT ID
            token_type: Type of token
            expires_at: Token expiration time
            user_id: User ID associated with token
            reason: Reason for blacklisting
            token_hash: Optional token hash for debugging

        Returns:
            Created blacklist entry
        """
        blacklist_entry = cls(
            jti=jti,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at,
            revocation_reason=reason,
            token_hash=token_hash
        )

        db.add(blacklist_entry)
        db.commit()
        db.refresh(blacklist_entry)

        return blacklist_entry

    @classmethod
    def blacklist_user_tokens(
        cls,
        db: Session,
        user_id: str,
        reason: str = "user_logout_all"
    ) -> int:
        """
        Blacklist all tokens for a specific user.

        Args:
            db: Database session
            user_id: User ID
            reason: Reason for blacklisting

        Returns:
            Number of tokens blacklisted
        """
        # Note: This is a simplified approach. In a real implementation,
        # you might want to track active tokens more explicitly.
        # For now, we'll create a special blacklist entry that invalidates
        # all tokens issued before this time.

        blacklist_entry = cls(
            jti=f"user_logout_all_{user_id}_{datetime.utcnow().timestamp()}",
            token_type="all",
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(days=30),  # Keep record for 30 days
            revocation_reason=reason
        )

        db.add(blacklist_entry)
        db.commit()

        return 1

    @classmethod
    def cleanup_expired_tokens(cls, db: Session) -> int:
        """
        Clean up expired blacklisted tokens.

        Args:
            db: Database session

        Returns:
            Number of tokens cleaned up
        """
        now = datetime.utcnow()

        deleted_count = (
            db.query(cls)
            .filter(cls.expires_at < now)
            .delete()
        )

        db.commit()
        return deleted_count

    @classmethod
    def get_user_blacklisted_tokens(
        cls,
        db: Session,
        user_id: str,
        limit: int = 50
    ) -> list["TokenBlacklist"]:
        """
        Get blacklisted tokens for a user.

        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of tokens to return

        Returns:
            List of blacklisted tokens
        """
        return (
            db.query(cls)
            .filter(cls.user_id == user_id)
            .order_by(cls.revoked_at.desc())
            .limit(limit)
            .all()
        )
