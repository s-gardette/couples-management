"""
Category model for expenses module.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as SQLAlchemyUUID
from sqlalchemy.orm import relationship

from app.core.models.base import BaseModel
from app.core.models.mixins import NameMixin, ActiveMixin


class Category(BaseModel, NameMixin, ActiveMixin):
    """Category model for organizing expenses."""
    
    __tablename__ = "categories"
    
    # Optional household association (null for global categories)
    household_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Optional icon identifier (e.g., "food", "transport", "entertainment")
    icon = Column(
        String(50),
        nullable=True
    )
    
    # Color for UI display (hex color code)
    color = Column(
        String(7),  # #RRGGBB format
        nullable=True,
        default="#6B7280"  # Default gray color
    )
    
    # Whether this is a default category
    is_default = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    
    # Relationships
    household = relationship(
        "Household",
        back_populates="categories"
    )
    
    expenses = relationship(
        "Expense",
        back_populates="category"
    )
    
    def __repr__(self) -> str:
        scope = "global" if self.household_id is None else f"household:{self.household_id}"
        return f"<Category(id={self.id}, name='{self.name}', scope='{scope}')>"
    
    @property
    def is_global(self) -> bool:
        """Check if this is a global category (not tied to a specific household)."""
        return self.household_id is None
    
    @property
    def is_household_specific(self) -> bool:
        """Check if this category belongs to a specific household."""
        return self.household_id is not None
    
    def set_icon(self, icon: Optional[str]) -> None:
        """Set the category icon."""
        self.icon = icon
    
    def set_color(self, color: str) -> None:
        """Set the category color (hex format)."""
        # Validate hex color format
        if color.startswith('#') and len(color) == 7:
            self.color = color
        else:
            raise ValueError("Color must be in hex format (#RRGGBB)")
    
    def make_default(self) -> None:
        """Mark this category as a default category."""
        self.is_default = True
    
    def remove_default(self) -> None:
        """Remove default status from this category."""
        self.is_default = False
    
    @classmethod
    def create_global_category(cls, name: str, icon: Optional[str] = None, color: str = "#6B7280", is_default: bool = False):
        """Create a new global category."""
        return cls(
            name=name,
            household_id=None,
            icon=icon,
            color=color,
            is_default=is_default,
            is_active=True
        )
    
    @classmethod
    def create_household_category(cls, name: str, household_id, icon: Optional[str] = None, color: str = "#6B7280", is_default: bool = False):
        """Create a new household-specific category."""
        # Convert string UUID to UUID object if needed
        if isinstance(household_id, str):
            household_id = UUID(household_id)
        
        return cls(
            name=name,
            household_id=household_id,
            icon=icon,
            color=color,
            is_default=is_default,
            is_active=True
        )
    
    @classmethod
    def get_default_categories(cls):
        """Get a list of default category definitions for seeding."""
        return [
            {"name": "Food & Dining", "icon": "utensils", "color": "#EF4444", "is_default": True},
            {"name": "Transportation", "icon": "car", "color": "#3B82F6", "is_default": True},
            {"name": "Shopping", "icon": "shopping-bag", "color": "#8B5CF6", "is_default": True},
            {"name": "Entertainment", "icon": "film", "color": "#F59E0B", "is_default": True},
            {"name": "Bills & Utilities", "icon": "receipt", "color": "#10B981", "is_default": True},
            {"name": "Healthcare", "icon": "heart", "color": "#EC4899", "is_default": True},
            {"name": "Home & Garden", "icon": "home", "color": "#6366F1", "is_default": True},
            {"name": "Travel", "icon": "plane", "color": "#14B8A6", "is_default": True},
            {"name": "Education", "icon": "book", "color": "#F97316", "is_default": True},
            {"name": "Other", "icon": "more-horizontal", "color": "#6B7280", "is_default": True},
        ] 