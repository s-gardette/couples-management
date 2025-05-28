"""
Email verification token model for authentication module.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.models.base import BaseModel
from app.config import settings


class EmailVerificationToken(BaseModel):
    """Model for email verification tokens."""
    
    __tablename__ = "email_verification_tokens"
    
    # Foreign key to user
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Token information
    token = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Token metadata
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime, nullable=True)
    
    # Relationship to user
    user = relationship("User", back_populates="email_verification_tokens")
    
    def __repr__(self) -> str:
        return f"<EmailVerificationToken(id={self.id}, user_id={self.user_id}, is_used={self.is_used})>"
    
    @classmethod
    def create_for_user(cls, user_id: UUID, token: str, expires_in_hours: int = 48):
        """Create a new email verification token for a user."""
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        return cls(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
    
    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired
    
    def use_token(self) -> None:
        """Mark the token as used."""
        self.is_used = True
        self.used_at = datetime.utcnow()
    
    def is_token_valid_for_verification(self) -> bool:
        """Check if token can be used for email verification."""
        return self.is_valid 