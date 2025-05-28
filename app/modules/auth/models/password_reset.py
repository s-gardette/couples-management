"""
Password reset token model for authentication module.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.models.base import BaseModel
from app.config import settings


class PasswordResetToken(BaseModel):
    """Model for password reset tokens."""
    
    __tablename__ = "password_reset_tokens"
    
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
    
    # Additional security
    ip_address = Column(String(45), nullable=True)  # Support IPv6
    user_agent = Column(String(500), nullable=True)
    
    # Relationship to user
    user = relationship("User", back_populates="password_reset_tokens")
    
    def __repr__(self) -> str:
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, is_used={self.is_used})>"
    
    @classmethod
    def create_for_user(
        cls, 
        user_id: UUID, 
        token: str, 
        expires_in_hours: int = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Create a new password reset token for a user."""
        if expires_in_hours is None:
            expires_in_hours = settings.email_reset_token_expire_hours
        
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        return cls(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
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
    
    def is_token_valid_for_reset(self) -> bool:
        """Check if token can be used for password reset."""
        return self.is_valid 