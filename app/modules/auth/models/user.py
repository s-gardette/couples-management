"""
User model for authentication module.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship

from app.core.models.base import BaseModel
from app.core.models.mixins import ActiveMixin


class User(BaseModel, ActiveMixin):
    """User model for authentication and user management."""
    
    __tablename__ = "users"
    
    # Basic user information
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    hashed_password = Column(
        String(255),
        nullable=False
    )
    
    # Personal information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Profile information
    avatar_url = Column(String(500), nullable=True)
    
    # Account status
    email_verified = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Note: is_active comes from ActiveMixin
    # Note: id, created_at, updated_at come from BaseModel
    
    # Relationships
    email_verification_tokens = relationship(
        "EmailVerificationToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    password_reset_tokens = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    sessions = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username
    
    @property
    def display_name(self) -> str:
        """Get user's display name (full name or username)."""
        return self.full_name if (self.first_name or self.last_name) else self.username
    
    def update_last_login(self) -> None:
        """Update the last login timestamp."""
        self.last_login_at = datetime.utcnow()
    
    def verify_email(self) -> None:
        """Mark email as verified."""
        self.email_verified = True
    
    def activate(self) -> None:
        """Activate the user account."""
        self.is_active = True
    
    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False 