"""
Pydantic schemas for payment system.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.modules.expenses.models.payment import PaymentType, PaymentMethod


# Base schemas
class PaymentBase(BaseModel):
    """Base payment schema with common fields."""
    amount: Decimal = Field(..., gt=0, description="Payment amount (must be positive)")
    currency: str = Field(default="USD", max_length=3, description="ISO 4217 currency code")
    payment_type: PaymentType = Field(default=PaymentType.REIMBURSEMENT, description="Type of payment")
    payment_method: Optional[PaymentMethod] = Field(None, description="Payment method used")
    description: Optional[str] = Field(None, max_length=500, description="Payment description")
    reference_number: Optional[str] = Field(None, max_length=100, description="Reference number (e.g., check number)")
    payment_date: Optional[datetime] = Field(None, description="When payment was made (defaults to now)")

    @validator('currency')
    def validate_currency(cls, v):
        """Validate currency code format."""
        if v and len(v) != 3:
            raise ValueError('Currency must be a 3-character ISO code')
        return v.upper() if v else "USD"


# Request schemas
class PaymentCreate(PaymentBase):
    """Schema for creating a new payment."""
    household_id: UUID = Field(..., description="Household ID")
    payer_id: UUID = Field(..., description="User ID who made the payment")
    payee_id: UUID = Field(..., description="User ID who received the payment")


class PaymentUpdate(BaseModel):
    """Schema for updating a payment."""
    amount: Optional[Decimal] = Field(None, gt=0, description="Updated payment amount")
    currency: Optional[str] = Field(None, max_length=3, description="Updated currency code")
    payment_method: Optional[PaymentMethod] = Field(None, description="Updated payment method")
    description: Optional[str] = Field(None, max_length=500, description="Updated description")
    reference_number: Optional[str] = Field(None, max_length=100, description="Updated reference number")
    payment_date: Optional[datetime] = Field(None, description="Updated payment date")

    @validator('currency')
    def validate_currency(cls, v):
        """Validate currency code format."""
        if v and len(v) != 3:
            raise ValueError('Currency must be a 3-character ISO code')
        return v.upper() if v else None


class PaymentFilters(BaseModel):
    """Schema for payment filtering parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    payer_id: Optional[UUID] = Field(None, description="Filter by payer")
    payee_id: Optional[UUID] = Field(None, description="Filter by payee")
    payment_type: Optional[PaymentType] = Field(None, description="Filter by payment type")
    payment_method: Optional[PaymentMethod] = Field(None, description="Filter by payment method")
    start_date: Optional[date] = Field(None, description="Filter payments from this date")
    end_date: Optional[date] = Field(None, description="Filter payments to this date")
    min_amount: Optional[Decimal] = Field(None, ge=0, description="Minimum payment amount")
    max_amount: Optional[Decimal] = Field(None, ge=0, description="Maximum payment amount")
    search: Optional[str] = Field(None, max_length=100, description="Search in description and reference")
    sort_by: str = Field(default="payment_date", description="Sort field")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")

    @validator('max_amount')
    def validate_amount_range(cls, v, values):
        """Validate that max_amount is greater than min_amount."""
        if v is not None and 'min_amount' in values and values['min_amount'] is not None:
            if v < values['min_amount']:
                raise ValueError('max_amount must be greater than or equal to min_amount')
        return v


# Response schemas
class UserSummary(BaseModel):
    """Summary user information for payment responses."""
    id: UUID
    username: str
    display_name: str
    
    class Config:
        from_attributes = True


class ExpenseShareSummary(BaseModel):
    """Summary expense share information for payment responses."""
    id: UUID
    expense_id: UUID
    expense_title: str
    share_amount: Decimal
    allocated_amount: Decimal
    
    class Config:
        from_attributes = True


class PaymentResponse(PaymentBase):
    """Schema for payment responses."""
    id: UUID
    household_id: UUID
    payer_id: Optional[UUID]
    payee_id: Optional[UUID]
    payer: Optional[UserSummary] = None
    payee: Optional[UserSummary] = None
    total_allocated_amount: Decimal
    unallocated_amount: Decimal
    is_fully_allocated: bool
    expense_shares: List[ExpenseShareSummary] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentListResponse(BaseModel):
    """Schema for paginated payment list responses."""
    payments: List[PaymentResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# Reimbursement workflow schemas
class DirectExpenseReimbursementRequest(BaseModel):
    """Schema for direct expense reimbursement request."""
    expense_id: UUID = Field(..., description="Expense ID to reimburse")
    payer_id: UUID = Field(..., description="User ID making the payment")
    payment_method: Optional[PaymentMethod] = Field(None, description="Payment method")
    description: Optional[str] = Field(None, max_length=500, description="Payment description")
    reference_number: Optional[str] = Field(None, max_length=100, description="Reference number")


class BulkExpensePaymentRequest(BaseModel):
    """Schema for bulk expense payment request."""
    household_id: UUID = Field(..., description="Household ID")
    target_user_id: UUID = Field(..., description="User whose expenses to pay")
    payer_id: UUID = Field(..., description="User making the payment")
    payment_method: Optional[PaymentMethod] = Field(None, description="Payment method")
    description: Optional[str] = Field(None, max_length=500, description="Payment description")
    reference_number: Optional[str] = Field(None, max_length=100, description="Reference number")


class ExpenseAllocation(BaseModel):
    """Schema for expense allocation in general payments."""
    expense_share_id: UUID = Field(..., description="Expense share ID")
    amount: Decimal = Field(..., gt=0, description="Amount to allocate to this expense")


class GeneralPaymentRequest(BaseModel):
    """Schema for general payment request."""
    household_id: UUID = Field(..., description="Household ID")
    payer_id: UUID = Field(..., description="User making the payment")
    payee_id: UUID = Field(..., description="User receiving the payment")
    amount: Decimal = Field(..., gt=0, description="Total payment amount")
    expense_allocations: Optional[List[ExpenseAllocation]] = Field(None, description="Optional expense allocations")
    payment_method: Optional[PaymentMethod] = Field(None, description="Payment method")
    description: Optional[str] = Field(None, max_length=500, description="Payment description")
    reference_number: Optional[str] = Field(None, max_length=100, description="Reference number")

    @validator('expense_allocations')
    def validate_allocations(cls, v, values):
        """Validate that total allocations don't exceed payment amount."""
        if v and 'amount' in values:
            total_allocated = sum(allocation.amount for allocation in v)
            if total_allocated > values['amount']:
                raise ValueError('Total allocations cannot exceed payment amount')
        return v


# Response schemas for reimbursement workflows
class ReimbursementResponse(BaseModel):
    """Schema for reimbursement workflow responses."""
    success: bool
    message: str
    payment: Optional[PaymentResponse] = None


# Balance and analytics schemas
class UserBalance(BaseModel):
    """Schema for user balance information."""
    user_id: UUID
    user: UserSummary
    total_owed: Decimal = Field(description="Total amount this user owes")
    total_owed_to: Decimal = Field(description="Total amount owed to this user")
    net_balance: Decimal = Field(description="Net balance (positive = owed to user, negative = user owes)")


class BalanceSummary(BaseModel):
    """Schema for household balance summary."""
    household_id: UUID
    total_expenses: Decimal
    total_payments: Decimal
    user_balances: List[UserBalance]
    last_updated: datetime


class PaymentHistoryEntry(BaseModel):
    """Schema for payment history entries."""
    payment: PaymentResponse
    related_expenses: List[ExpenseShareSummary]


class PaymentHistoryResponse(BaseModel):
    """Schema for payment history response."""
    household_id: UUID
    payments: List[PaymentHistoryEntry]
    total: int
    page: int
    per_page: int
    total_pages: int


class UserPaymentSummary(BaseModel):
    """Schema for user payment summary."""
    user_id: UUID
    user: UserSummary
    total_paid: Decimal = Field(description="Total amount paid by user")
    total_received: Decimal = Field(description="Total amount received by user")
    payment_count: int = Field(description="Number of payments made")
    recent_payments: List[PaymentResponse] = Field(description="Recent payment activity")


# Link/unlink expense share schemas
class LinkExpenseShareRequest(BaseModel):
    """Schema for linking payment to expense share."""
    expense_share_id: UUID = Field(..., description="Expense share ID to link")
    amount: Decimal = Field(..., gt=0, description="Amount to allocate")


class LinkExpenseShareResponse(BaseModel):
    """Schema for link expense share response."""
    success: bool
    message: str
    expense_share_payment_id: Optional[UUID] = None


# Unpaid expenses schemas
class UnpaidExpenseInfo(BaseModel):
    """Schema for unpaid expense information."""
    expense_id: UUID
    expense_share_id: UUID
    title: str
    description: Optional[str]
    total_amount: Decimal
    share_amount: Decimal
    currency: str
    expense_date: date
    category: Optional[str]
    formatted_share_amount: str


class UnpaidExpensesResponse(BaseModel):
    """Schema for unpaid expenses response."""
    expenses: List[UnpaidExpenseInfo]
    total_owed: Decimal
    count: int 