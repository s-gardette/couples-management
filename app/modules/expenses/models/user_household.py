"""
UserHousehold association model for expenses module.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.models.base import BaseModel
from app.core.models.mixins import ActiveMixin
from .household import UserHouseholdRole, get_enum_values


class UserHousehold(BaseModel, ActiveMixin):
    """Association model for users and households with role and metadata."""
    
    __tablename__ = "user_households"
    
    # Foreign keys
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    household_id = Column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Role within the household
    role = Column(
        SQLEnum(UserHouseholdRole, name='userhouseholdrole', values_callable=get_enum_values),
        default=UserHouseholdRole.MEMBER,
        nullable=False,
        index=True
    )
    
    # Optional display name within the household
    nickname = Column(
        String(100),
        nullable=True
    )
    
    # When the user joined the household
    joined_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # Relationships
    user = relationship(
        "User",
        backref="household_memberships"
    )
    
    household = relationship(
        "Household",
        back_populates="members"
    )
    
    expense_shares = relationship(
        "ExpenseShare",
        back_populates="user_household",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<UserHousehold(user_id={self.user_id}, household_id={self.household_id}, role='{self.role}')>"
    
    @property
    def display_name(self) -> str:
        """Get the display name for this user in this household."""
        if self.nickname:
            return self.nickname
        elif self.user:
            return self.user.display_name
        else:
            return "Unknown User"
    
    def is_admin(self) -> bool:
        """Check if this user has admin role in the household."""
        return self.role == UserHouseholdRole.ADMIN
    
    def is_member(self) -> bool:
        """Check if this user has member role in the household."""
        return self.role == UserHouseholdRole.MEMBER
    
    def promote_to_admin(self) -> None:
        """Promote user to admin role."""
        self.role = UserHouseholdRole.ADMIN
    
    def demote_to_member(self) -> None:
        """Demote user to member role."""
        self.role = UserHouseholdRole.MEMBER
    
    def set_nickname(self, nickname: Optional[str]) -> None:
        """Set or update the user's nickname in this household."""
        self.nickname = nickname
    
    def leave_household(self) -> None:
        """Mark the user as having left the household."""
        self.is_active = False
    
    def rejoin_household(self) -> None:
        """Mark the user as active in the household again."""
        self.is_active = True
        self.joined_at = datetime.utcnow()
    
    @classmethod
    def create_membership(cls, user_id: str, household_id: str, role: UserHouseholdRole = UserHouseholdRole.MEMBER, nickname: Optional[str] = None):
        """Create a new household membership."""
        return cls(
            user_id=user_id,
            household_id=household_id,
            role=role,
            nickname=nickname,
            joined_at=datetime.utcnow(),
            is_active=True
        ) 