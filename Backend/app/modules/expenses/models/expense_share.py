"""
ExpenseShare model for expenses module.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, String, DECIMAL, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.models.base import BaseModel
from app.core.models.mixins import ActiveMixin


class ExpenseShare(BaseModel, ActiveMixin):
    """ExpenseShare model for tracking how expenses are split between users."""
    
    __tablename__ = "expense_shares"
    
    # Expense this share belongs to
    expense_id = Column(
        UUID(as_uuid=True),
        ForeignKey("expenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # User household membership (links user to household)
    user_household_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_households.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Share amount (the actual amount this user owes)
    share_amount = Column(
        DECIMAL(precision=10, scale=2),
        nullable=False,
        index=True
    )
    
    # Optional: share percentage (for percentage-based splits)
    share_percentage = Column(
        DECIMAL(precision=5, scale=2),  # 0.00 to 100.00
        nullable=True
    )
    
    # Payment status
    is_paid = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    
    # When the share was paid
    paid_at = Column(
        DateTime,
        nullable=True,
        index=True
    )
    
    # Optional payment method
    payment_method = Column(
        String(50),
        nullable=True
    )
    
    # Optional notes about the payment
    payment_notes = Column(
        String(500),
        nullable=True
    )
    
    # Relationships
    expense = relationship(
        "Expense",
        back_populates="shares"
    )
    
    user_household = relationship(
        "UserHousehold",
        back_populates="expense_shares"
    )
    
    payments = relationship(
        "ExpenseSharePayment",
        back_populates="expense_share",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        status = "paid" if self.is_paid else "unpaid"
        return f"<ExpenseShare(expense_id={self.expense_id}, user_household_id={self.user_household_id}, amount={self.share_amount}, status={status})>"
    
    @property
    def share_amount_decimal(self) -> Decimal:
        """Get the share amount as a Decimal object."""
        return Decimal(str(self.share_amount))
    
    @property
    def share_percentage_decimal(self) -> Optional[Decimal]:
        """Get the share percentage as a Decimal object."""
        if self.share_percentage is not None:
            return Decimal(str(self.share_percentage))
        return None
    
    @property
    def formatted_amount(self) -> str:
        """Get formatted share amount with currency symbol."""
        if self.expense:
            currency_symbols = {
                "USD": "$",
                "EUR": "€",
                "GBP": "£",
                "JPY": "¥",
                "CAD": "C$",
                "AUD": "A$",
            }
            symbol = currency_symbols.get(self.expense.currency, self.expense.currency)
            return f"{symbol}{self.share_amount:.2f}"
        return f"${self.share_amount:.2f}"
    
    @property
    def user_display_name(self) -> str:
        """Get the display name of the user this share belongs to."""
        if self.user_household:
            return self.user_household.display_name
        return "Unknown User"
    
    @property
    def user_id(self) -> Optional[str]:
        """Get the user ID for this share."""
        if self.user_household and self.user_household.user:
            return str(self.user_household.user.id)
        return None
    
    @property
    def username(self) -> Optional[str]:
        """Get the username for this share."""
        if self.user_household and self.user_household.user:
            return self.user_household.user.username
        return None
    
    @property
    def days_since_expense(self) -> int:
        """Get the number of days since the expense was created."""
        if self.expense:
            delta = datetime.utcnow().date() - self.expense.expense_date
            return delta.days
        return 0
    
    @property
    def days_since_paid(self) -> Optional[int]:
        """Get the number of days since this share was paid."""
        if self.paid_at:
            delta = datetime.utcnow() - self.paid_at
            return delta.days
        return None
    
    def mark_as_paid(self, payment_method: Optional[str] = None, payment_notes: Optional[str] = None) -> None:
        """Mark this share as paid."""
        self.is_paid = True
        self.paid_at = datetime.utcnow()
        if payment_method:
            self.payment_method = payment_method
        if payment_notes:
            self.payment_notes = payment_notes
    
    def mark_as_unpaid(self) -> None:
        """Mark this share as unpaid."""
        self.is_paid = False
        self.paid_at = None
        self.payment_method = None
        self.payment_notes = None
    
    def update_amount(self, new_amount: Decimal) -> None:
        """Update the share amount."""
        self.share_amount = new_amount
    
    def update_percentage(self, new_percentage: Optional[Decimal]) -> None:
        """Update the share percentage."""
        self.share_percentage = new_percentage
    
    def set_payment_method(self, payment_method: str) -> None:
        """Set the payment method for this share."""
        self.payment_method = payment_method
    
    def add_payment_notes(self, notes: str) -> None:
        """Add notes about the payment."""
        self.payment_notes = notes
    
    @classmethod
    def create_share(cls, expense_id: str, user_household_id: str, share_amount: Decimal, share_percentage: Optional[Decimal] = None):
        """Create a new expense share."""
        return cls(
            expense_id=expense_id,
            user_household_id=user_household_id,
            share_amount=share_amount,
            share_percentage=share_percentage,
            is_paid=False,
            is_active=True
        )
    
    @classmethod
    def create_equal_share(cls, expense_id: str, user_household_id: str, total_amount: Decimal, num_people: int):
        """Create an equal share for an expense."""
        share_amount = total_amount / num_people
        share_percentage = Decimal('100.00') / num_people
        return cls.create_share(expense_id, user_household_id, share_amount, share_percentage)
    
    @classmethod
    def create_percentage_share(cls, expense_id: str, user_household_id: str, total_amount: Decimal, percentage: Decimal):
        """Create a percentage-based share for an expense."""
        share_amount = (total_amount * percentage) / Decimal('100.00')
        return cls.create_share(expense_id, user_household_id, share_amount, percentage) 