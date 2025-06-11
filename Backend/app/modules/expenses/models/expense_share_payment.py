"""
ExpenseSharePayment model for linking payments to expense shares.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, DECIMAL, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.models.base import BaseModel
from app.core.models.mixins import ActiveMixin


class ExpenseSharePayment(BaseModel, ActiveMixin):
    """Links payments to expense shares, allowing payments to cover multiple expense shares."""
    
    __tablename__ = "expense_share_payments"
    
    # Payment this link belongs to
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Expense share being paid
    expense_share_id = Column(
        UUID(as_uuid=True),
        ForeignKey("expense_shares.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Amount of the payment allocated to this expense share
    amount = Column(
        DECIMAL(precision=10, scale=2),
        nullable=False,
        index=True
    )
    
    # When this allocation was created
    allocated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    # Relationships
    payment = relationship(
        "Payment",
        back_populates="expense_share_payments"
    )
    
    expense_share = relationship(
        "ExpenseShare",
        back_populates="payments"
    )
    
    def __repr__(self) -> str:
        return f"<ExpenseSharePayment(payment_id={self.payment_id}, expense_share_id={self.expense_share_id}, amount={self.amount})>"
    
    @property
    def amount_decimal(self) -> Decimal:
        """Get the amount as a Decimal object."""
        return Decimal(str(self.amount))
    
    @property
    def formatted_amount(self) -> str:
        """Get formatted amount with currency symbol."""
        if self.expense_share and self.expense_share.expense:
            currency_symbols = {
                "USD": "$",
                "EUR": "€",
                "GBP": "£",
                "JPY": "¥",
                "CAD": "C$",
                "AUD": "A$",
            }
            symbol = currency_symbols.get(self.expense_share.expense.currency, self.expense_share.expense.currency)
            return f"{symbol}{self.amount:.2f}"
        return f"${self.amount:.2f}"
    
    @property
    def covers_full_share(self) -> bool:
        """Check if this payment allocation covers the full expense share amount."""
        if self.expense_share:
            return abs(self.amount_decimal - self.expense_share.share_amount_decimal) < Decimal('0.01')
        return False
    
    @property
    def coverage_percentage(self) -> Optional[Decimal]:
        """Get what percentage of the expense share this payment covers."""
        if self.expense_share and self.expense_share.share_amount > 0:
            return (self.amount_decimal / self.expense_share.share_amount_decimal) * Decimal('100')
        return None
    
    def update_amount(self, new_amount: Decimal) -> None:
        """Update the allocation amount."""
        self.amount = new_amount
        self.allocated_at = datetime.utcnow()
    
    @classmethod
    def create_allocation(
        cls,
        payment_id: UUID,
        expense_share_id: UUID,
        amount: Decimal
    ):
        """Create a new payment allocation to an expense share."""
        return cls(
            payment_id=payment_id,
            expense_share_id=expense_share_id,
            amount=amount,
            is_active=True
        )
    
    @classmethod
    def create_full_allocation(cls, payment_id: UUID, expense_share):
        """Create an allocation that covers the full expense share amount."""
        return cls.create_allocation(
            payment_id=payment_id,
            expense_share_id=expense_share.id,
            amount=expense_share.share_amount_decimal
        ) 