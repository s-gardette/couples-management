"""
Payment model for tracking reimbursements and payments.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Text, DECIMAL, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.models.base import BaseModel
from app.core.models.mixins import ActiveMixin


class PaymentType(PyEnum):
    """Types of payments."""
    REIMBURSEMENT = "reimbursement"  # General reimbursement payment
    EXPENSE_PAYMENT = "expense_payment"  # Payment specifically for expenses
    ADJUSTMENT = "adjustment"  # Balance adjustment


class PaymentMethod(PyEnum):
    """Payment methods."""
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    DIGITAL_WALLET = "digital_wallet"
    CHECK = "check"
    OTHER = "other"


class Payment(BaseModel, ActiveMixin):
    """Payment model for tracking reimbursements and payments between users."""
    
    __tablename__ = "payments"
    
    # Household this payment belongs to
    household_id = Column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Who made the payment (payer)
    payer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Who received the payment (payee)
    payee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Payment details
    amount = Column(
        DECIMAL(precision=10, scale=2),
        nullable=False,
        index=True
    )
    
    currency = Column(
        String(3),  # ISO 4217 currency codes
        nullable=False,
        default="USD",
        index=True
    )
    
    payment_type = Column(
        Enum(PaymentType),
        nullable=False,
        default=PaymentType.REIMBURSEMENT,
        index=True
    )
    
    payment_method = Column(
        Enum(PaymentMethod),
        nullable=True,
        index=True
    )
    
    # When the payment was made
    payment_date = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    # Description/notes
    description = Column(
        Text,
        nullable=True
    )
    
    # Optional reference number (bank transfer, check number, etc.)
    reference_number = Column(
        String(100),
        nullable=True
    )
    
    # Relationships
    household = relationship(
        "Household",
        back_populates="payments"
    )
    
    payer = relationship(
        "User",
        foreign_keys=[payer_id],
        backref="payments_made"
    )
    
    payee = relationship(
        "User", 
        foreign_keys=[payee_id],
        backref="payments_received"
    )
    
    # Relationship to expense shares this payment covers
    expense_share_payments = relationship(
        "ExpenseSharePayment",
        back_populates="payment",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, amount={self.amount} {self.currency}, type={self.payment_type.value})>"
    
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
    def payer_name(self) -> str:
        """Get the payer's display name."""
        if self.payer:
            return self.payer.display_name
        return "Unknown"
    
    @property
    def payee_name(self) -> str:
        """Get the payee's display name."""
        if self.payee:
            return self.payee.display_name
        return "Unknown"
    
    @property
    def total_allocated_amount(self) -> Decimal:
        """Get the total amount allocated to expense shares."""
        return sum(
            Decimal(str(esp.amount)) 
            for esp in self.expense_share_payments 
            if esp.is_active
        )
    
    @property
    def unallocated_amount(self) -> Decimal:
        """Get the amount not yet allocated to specific expense shares."""
        return self.amount_decimal - self.total_allocated_amount
    
    @property
    def covered_expense_shares(self) -> List:
        """Get the expense shares covered by this payment."""
        return [esp.expense_share for esp in self.expense_share_payments if esp.is_active]
    
    @property
    def is_fully_allocated(self) -> bool:
        """Check if the payment is fully allocated to expense shares."""
        return abs(self.unallocated_amount) < Decimal('0.01')
    
    def add_expense_share(self, expense_share, amount: Decimal) -> None:
        """Add an expense share to this payment."""
        from .expense_share_payment import ExpenseSharePayment
        
        esp = ExpenseSharePayment(
            payment_id=self.id,
            expense_share_id=expense_share.id,
            amount=amount
        )
        self.expense_share_payments.append(esp)
    
    def remove_expense_share(self, expense_share) -> None:
        """Remove an expense share from this payment."""
        for esp in self.expense_share_payments:
            if esp.expense_share_id == expense_share.id and esp.is_active:
                esp.is_active = False
                break
    
    def set_payment_method(self, method: PaymentMethod, reference: Optional[str] = None) -> None:
        """Set the payment method and optional reference."""
        self.payment_method = method
        if reference:
            self.reference_number = reference
    
    def add_description(self, description: str) -> None:
        """Add or update the payment description."""
        self.description = description
    
    @classmethod
    def create_reimbursement(
        cls,
        household_id: str,
        payer_id: str,
        payee_id: str,
        amount: Decimal,
        currency: str = "USD",
        payment_method: Optional[PaymentMethod] = None,
        description: Optional[str] = None,
        reference_number: Optional[str] = None
    ):
        """Create a general reimbursement payment."""
        return cls(
            household_id=household_id,
            payer_id=payer_id,
            payee_id=payee_id,
            amount=amount,
            currency=currency,
            payment_type=PaymentType.REIMBURSEMENT,
            payment_method=payment_method,
            description=description,
            reference_number=reference_number,
            is_active=True
        )
    
    @classmethod
    def create_expense_payment(
        cls,
        household_id: str,
        payer_id: str,
        payee_id: str,
        amount: Decimal,
        expense_shares: List,
        currency: str = "USD",
        payment_method: Optional[PaymentMethod] = None,
        description: Optional[str] = None,
        reference_number: Optional[str] = None
    ):
        """Create a payment specifically for covering expense shares."""
        payment = cls(
            household_id=household_id,
            payer_id=payer_id,
            payee_id=payee_id,
            amount=amount,
            currency=currency,
            payment_type=PaymentType.EXPENSE_PAYMENT,
            payment_method=payment_method,
            description=description,
            reference_number=reference_number,
            is_active=True
        )
        
        # Link expense shares
        for expense_share, share_amount in expense_shares:
            payment.add_expense_share(expense_share, share_amount)
        
        return payment 