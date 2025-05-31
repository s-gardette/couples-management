"""
Pydantic schemas for expense-related API endpoints.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, validator


class ExpenseBase(BaseModel):
    """Base schema for expense data."""
    title: str = Field(..., min_length=1, max_length=200, description="Expense title")
    description: Optional[str] = Field(None, max_length=1000, description="Expense description")
    amount: Decimal = Field(..., gt=0, description="Expense amount")
    currency: str = Field(default="USD", max_length=3, description="Currency code")
    expense_date: date = Field(..., description="Date of the expense")
    tags: Optional[List[str]] = Field(default_factory=list, description="Expense tags")


class ExpenseCreate(ExpenseBase):
    """Schema for creating a new expense."""
    category_id: UUID = Field(..., description="Category ID for the expense")
    split_method: str = Field(default="equal", description="Split method: equal, percentage, custom")
    split_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Split configuration data")


class ExpenseUpdate(BaseModel):
    """Schema for updating an expense."""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Expense title")
    description: Optional[str] = Field(None, max_length=1000, description="Expense description")
    amount: Optional[Decimal] = Field(None, gt=0, description="Expense amount")
    currency: Optional[str] = Field(None, max_length=3, description="Currency code")
    category_id: Optional[UUID] = Field(None, description="Category ID for the expense")
    expense_date: Optional[date] = Field(None, description="Date of the expense")
    tags: Optional[List[str]] = Field(None, description="Expense tags")


class ExpenseShareResponse(BaseModel):
    """Schema for expense share information."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    username: str
    share_amount: Decimal
    share_percentage: Optional[Decimal] = None
    is_paid: bool
    paid_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    payment_notes: Optional[str] = None


class CategoryResponse(BaseModel):
    """Schema for category information."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    icon: Optional[str] = None
    color: str
    is_default: bool


class ExpenseResponse(ExpenseBase):
    """Schema for expense response data."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    household_id: UUID
    created_by: UUID
    created_by_username: Optional[str] = None
    category: Optional[CategoryResponse] = None
    receipt_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    # Expense shares
    shares: Optional[List[ExpenseShareResponse]] = None
    total_paid: Optional[Decimal] = None
    total_unpaid: Optional[Decimal] = None


class ExpenseListResponse(BaseModel):
    """Schema for expense list response."""
    expenses: List[ExpenseResponse]
    total: int
    page: int
    per_page: int
    total_amount: Decimal
    paid_amount: Decimal
    unpaid_amount: Decimal


class ExpenseFilters(BaseModel):
    """Schema for expense filtering parameters."""
    category_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    tags: Optional[List[str]] = None
    is_paid: Optional[bool] = None
    search: Optional[str] = None


class UpdateExpenseSharesRequest(BaseModel):
    """Schema for updating expense shares."""
    split_method: str = Field(..., description="Split method: equal, percentage, custom")
    split_data: Dict[str, Any] = Field(..., description="Split configuration data")
    recalculate_existing: bool = Field(default=True, description="Whether to recalculate existing shares")


class MarkSharePaidRequest(BaseModel):
    """Schema for marking a share as paid."""
    payment_method: Optional[str] = Field(None, max_length=50, description="Payment method used")
    payment_notes: Optional[str] = Field(None, max_length=500, description="Payment notes")


class ExpenseSummaryResponse(BaseModel):
    """Schema for expense summary data."""
    total_expenses: int
    total_amount: Decimal
    paid_amount: Decimal
    unpaid_amount: Decimal
    average_expense: Decimal
    categories_breakdown: Dict[str, Dict[str, Any]]
    monthly_breakdown: Dict[str, Decimal]
    user_breakdown: Dict[str, Dict[str, Any]]


class ReceiptUploadResponse(BaseModel):
    """Schema for receipt upload response."""
    receipt_url: str
    expense_id: UUID
    uploaded_at: datetime
    file_size: int
    file_type: str 