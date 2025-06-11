"""
Pydantic schemas for category-related API endpoints.
"""

from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, validator


class CategoryBase(BaseModel):
    """Base schema for category data."""
    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    icon: Optional[str] = Field(None, max_length=50, description="Category icon identifier")
    color: str = Field(default="#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$", description="Category color in hex format")


class CategoryCreate(CategoryBase):
    """Schema for creating a new category."""
    is_default: bool = Field(default=False, description="Whether this is a default category")


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Category name")
    icon: Optional[str] = Field(None, max_length=50, description="Category icon identifier")
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Category color in hex format")


class CategoryResponse(CategoryBase):
    """Schema for category response data."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    household_id: Optional[UUID] = None
    is_default: bool
    is_global: bool = False
    expense_count: Optional[int] = None
    total_amount: Optional[float] = None


class CategoryListResponse(BaseModel):
    """Schema for category list response."""
    categories: List[CategoryResponse]
    total: int
    global_categories: List[CategoryResponse]
    household_categories: List[CategoryResponse]


class CategoryStatsResponse(BaseModel):
    """Schema for category statistics."""
    category_id: UUID
    category_name: str
    expense_count: int
    total_amount: float
    average_amount: float
    percentage_of_total: float
    color: str
    icon: Optional[str] = None 