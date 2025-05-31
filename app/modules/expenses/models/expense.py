"""
Expense model for expenses module.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Column, String, Text, Date, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.core.models.base import BaseModel
from app.core.models.mixins import ActiveMixin


class Expense(BaseModel, ActiveMixin):
    """Expense model for tracking household expenses."""
    
    __tablename__ = "expenses"
    
    # Household this expense belongs to
    household_id = Column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # User who created the expense
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Expense details
    title = Column(
        String(255),
        nullable=False,
        index=True
    )
    
    description = Column(
        Text,
        nullable=True
    )
    
    # Amount and currency
    amount = Column(
        DECIMAL(precision=10, scale=2),
        nullable=False,
        index=True
    )
    
    currency = Column(
        String(3),  # ISO 4217 currency codes (USD, EUR, etc.)
        nullable=False,
        default="USD",
        index=True
    )
    
    # Category
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # When the expense occurred
    expense_date = Column(
        Date,
        nullable=False,
        default=date.today,
        index=True
    )
    
    # Optional receipt image/document
    receipt_url = Column(
        String(500),
        nullable=True
    )
    
    # Tags for additional categorization (using PostgreSQL ARRAY)
    tags = Column(
        ARRAY(String),
        nullable=True,
        default=None
    )
    
    # Relationships
    household = relationship(
        "Household",
        back_populates="expenses"
    )
    
    creator = relationship(
        "User",
        foreign_keys=[created_by],
        backref="created_expenses"
    )
    
    category = relationship(
        "Category",
        back_populates="expenses"
    )
    
    shares = relationship(
        "ExpenseShare",
        back_populates="expense",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Expense(id={self.id}, title='{self.title}', amount={self.amount} {self.currency})>"
    
    @property
    def amount_decimal(self) -> Decimal:
        """Get the amount as a Decimal object."""
        return Decimal(str(self.amount))
    
    @property
    def formatted_amount(self) -> str:
        """Get formatted amount with currency symbol."""
        currency_symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
            "CAD": "C$",
            "AUD": "A$",
        }
        symbol = currency_symbols.get(self.currency, self.currency)
        return f"{symbol}{self.amount:.2f}"
    
    @property
    def total_shares_amount(self) -> Decimal:
        """Get the total amount of all shares."""
        return sum(Decimal(str(share.share_amount)) for share in self.shares if share.is_active)
    
    @property
    def is_fully_shared(self) -> bool:
        """Check if the expense is fully allocated to shares."""
        return abs(self.amount_decimal - self.total_shares_amount) < Decimal('0.01')
    
    @property
    def remaining_amount(self) -> Decimal:
        """Get the remaining amount not yet allocated to shares."""
        return self.amount_decimal - self.total_shares_amount
    
    @property
    def paid_shares_count(self) -> int:
        """Get the number of shares that have been paid."""
        return len([share for share in self.shares if share.is_active and share.is_paid])
    
    @property
    def unpaid_shares_count(self) -> int:
        """Get the number of shares that haven't been paid."""
        return len([share for share in self.shares if share.is_active and not share.is_paid])
    
    @property
    def is_fully_paid(self) -> bool:
        """Check if all shares of this expense have been paid."""
        return self.unpaid_shares_count == 0 and len(self.shares) > 0
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the expense."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the expense."""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if the expense has a specific tag."""
        return self.tags is not None and tag in self.tags
    
    def set_receipt(self, receipt_url: str) -> None:
        """Set the receipt URL for this expense."""
        self.receipt_url = receipt_url
    
    def remove_receipt(self) -> None:
        """Remove the receipt from this expense."""
        self.receipt_url = None
    
    def get_share_for_user(self, user_id: str):
        """Get the expense share for a specific user."""
        for share in self.shares:
            if share.user_household.user_id == user_id and share.is_active:
                return share
        return None
    
    def get_active_shares(self):
        """Get all active shares for this expense."""
        return [share for share in self.shares if share.is_active]
    
    def get_paid_shares(self):
        """Get all paid shares for this expense."""
        return [share for share in self.shares if share.is_active and share.is_paid]
    
    def get_unpaid_shares(self):
        """Get all unpaid shares for this expense."""
        return [share for share in self.shares if share.is_active and not share.is_paid] 