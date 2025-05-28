"""
User model for authentication module.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, String, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.models.base import BaseModel
from app.core.models.mixins import ActiveMixin


def get_enum_values(enum_class):
    """Get enum values for SQLAlchemy enum column."""
    return [member.value for member in enum_class]


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"


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
    
    # Role and permissions
    role = Column(
        SQLEnum(UserRole, name='userrole', values_callable=get_enum_values),
        default=UserRole.USER,
        nullable=False,
        index=True
    )
    
    # Personal information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Profile information
    avatar_url = Column(String(500), nullable=True)
    
    # Account status
    email_verified = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Admin-specific fields
    created_by_admin_id = Column(String(36), nullable=True)  # UUID of admin who created this user
    requires_password_change = Column(Boolean, default=False, nullable=False)  # Force password change on first login
    
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
    password_history = relationship(
        "PasswordHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="PasswordHistory.changed_at.desc()"
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
    
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN
    
    def is_regular_user(self) -> bool:
        """Check if user has regular user role."""
        return self.role == UserRole.USER
    
    def make_admin(self) -> None:
        """Promote user to admin role."""
        self.role = UserRole.ADMIN
    
    def make_user(self) -> None:
        """Demote user to regular user role."""
        self.role = UserRole.USER
    
    def set_created_by_admin(self, admin_id: str) -> None:
        """Set the admin who created this user."""
        self.created_by_admin_id = admin_id
    
    def require_password_change(self) -> None:
        """Force user to change password on next login."""
        self.requires_password_change = True
    
    def password_changed(self) -> None:
        """Mark that user has changed their password."""
        self.requires_password_change = False 