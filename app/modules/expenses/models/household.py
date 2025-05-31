"""
Household model for expenses module.
"""

from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, String, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.models.base import BaseModel
from app.core.models.mixins import ActiveMixin, NameMixin, DescriptionMixin


def get_enum_values(enum_class):
    """Get enum values for SQLAlchemy enum column."""
    return [member.value for member in enum_class]


class UserHouseholdRole(str, Enum):
    """User role within a household."""
    ADMIN = "admin"
    MEMBER = "member"


class Household(BaseModel, NameMixin, DescriptionMixin, ActiveMixin):
    """Household model for managing shared expenses."""
    
    __tablename__ = "households"
    
    # Unique invite code for joining the household
    invite_code = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Creator of the household
    created_by = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Household settings (JSON field for preferences)
    settings = Column(
        JSON,
        nullable=True,
        default=lambda: {
            "default_currency": "USD",
            "allow_member_invites": True,
            "require_receipt_for_large_expenses": False,
            "large_expense_threshold": 100.00,
            "default_split_method": "equal",
            "timezone": "UTC"
        }
    )
    
    # Relationships
    creator = relationship(
        "User",
        foreign_keys=[created_by],
        backref="created_households"
    )
    
    members = relationship(
        "UserHousehold",
        back_populates="household",
        cascade="all, delete-orphan"
    )
    
    expenses = relationship(
        "Expense",
        back_populates="household",
        cascade="all, delete-orphan"
    )
    
    categories = relationship(
        "Category",
        back_populates="household",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Household(id={self.id}, name='{self.name}', invite_code='{self.invite_code}')>"
    
    @property
    def member_count(self) -> int:
        """Get the number of active members in the household."""
        return len([m for m in self.members if m.is_active])
    
    @property
    def admin_count(self) -> int:
        """Get the number of admin members in the household."""
        return len([m for m in self.members if m.is_active and m.role == UserHouseholdRole.ADMIN])
    
    def get_setting(self, key: str, default=None):
        """Get a specific setting value."""
        if self.settings:
            return self.settings.get(key, default)
        return default
    
    def update_setting(self, key: str, value):
        """Update a specific setting value."""
        if self.settings is None:
            self.settings = {}
        self.settings[key] = value
    
    def get_active_members(self):
        """Get all active members of the household."""
        return [m for m in self.members if m.is_active]
    
    def get_admins(self):
        """Get all admin members of the household."""
        return [m for m in self.members if m.is_active and m.role == UserHouseholdRole.ADMIN]
    
    def is_member(self, user_id: str) -> bool:
        """Check if a user is a member of this household."""
        # Convert string to UUID for comparison
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            return any(m.user_id == user_uuid and m.is_active for m in self.members)
        except (ValueError, TypeError):
            # If conversion fails, try string comparison
            return any(str(m.user_id) == str(user_id) and m.is_active for m in self.members)
    
    def is_admin(self, user_id: str) -> bool:
        """Check if a user is an admin of this household."""
        # Convert string to UUID for comparison
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            return any(
                m.user_id == user_uuid and m.is_active and m.role == UserHouseholdRole.ADMIN 
                for m in self.members
            )
        except (ValueError, TypeError):
            # If conversion fails, try string comparison
            return any(
                str(m.user_id) == str(user_id) and m.is_active and m.role == UserHouseholdRole.ADMIN 
                for m in self.members
            )
    
    def get_member(self, user_id: str):
        """Get a specific member by user ID."""
        # Convert string to UUID for comparison
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            for member in self.members:
                if member.user_id == user_uuid and member.is_active:
                    return member
        except (ValueError, TypeError):
            # If conversion fails, try string comparison
            for member in self.members:
                if str(member.user_id) == str(user_id) and member.is_active:
                    return member
        return None 