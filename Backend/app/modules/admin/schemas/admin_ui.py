"""
Admin UI schemas for data validation and API responses.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SystemHealthCheckResponse(BaseModel):
    """Schema for system health check responses."""
    status: str = Field(..., description="Health status (healthy, degraded, error)")
    message: str = Field(..., description="Health status message")


class SystemMetricsResponse(BaseModel):
    """Schema for system metrics."""
    response_time: str = Field(..., description="Average response time")
    error_rate: str = Field(..., description="Error rate percentage")
    uptime: str = Field(..., description="System uptime percentage")


class SystemHealthResponse(BaseModel):
    """Schema for system health response."""
    overall_status: str = Field(..., description="Overall system status")
    checks: Dict[str, SystemHealthCheckResponse] = Field(..., description="Individual health checks")
    metrics: SystemMetricsResponse = Field(..., description="System metrics")
    last_check: str = Field(..., description="Last health check timestamp")


class UserStatsResponse(BaseModel):
    """Schema for user statistics."""
    total: int = Field(..., description="Total user count")
    active: int = Field(..., description="Active user count")
    admin: int = Field(..., description="Admin user count")
    new_30d: int = Field(..., description="New users in last 30 days")


class HouseholdStatsResponse(BaseModel):
    """Schema for household statistics."""
    total: int = Field(..., description="Total household count")
    active: int = Field(..., description="Active household count")
    new_30d: int = Field(..., description="New households in last 30 days")


class ExpenseStatsResponse(BaseModel):
    """Schema for expense statistics."""
    total: int = Field(..., description="Total expense count")
    total_amount: float = Field(..., description="Total expense amount")
    new_30d: int = Field(..., description="New expenses in last 30 days")


class SystemStatsResponse(BaseModel):
    """Schema for system statistics."""
    database_status: str = Field(..., description="Database status")
    last_updated: str = Field(..., description="Last update timestamp")


class SystemOverviewResponse(BaseModel):
    """Schema for system overview response."""
    users: Dict[str, int]
    households: Dict[str, int]
    expenses: Dict[str, Any]
    system: Dict[str, Any]


class ActivityResponse(BaseModel):
    """Schema for system activity response."""
    type: str = Field(..., description="Activity type")
    title: str = Field(..., description="Activity title")
    description: str = Field(..., description="Activity description")
    timestamp: datetime = Field(..., description="Activity timestamp")
    user_id: Optional[str] = Field(None, description="Associated user ID")
    user_name: Optional[str] = Field(None, description="Associated user name")
    user_email: Optional[str] = Field(None, description="Associated user email")
    household_id: Optional[str] = Field(None, description="Associated household ID")
    household_name: Optional[str] = Field(None, description="Associated household name")
    expense_id: Optional[str] = Field(None, description="Associated expense ID")
    expense_title: Optional[str] = Field(None, description="Associated expense title")
    expense_amount: Optional[float] = Field(None, description="Associated expense amount")


class TodayStatsResponse(BaseModel):
    """Schema for today's statistics."""
    new_users: int = Field(..., description="New users today")
    new_expenses: int = Field(..., description="New expenses today")
    expense_amount: float = Field(..., description="Total expense amount today")


class QuickStatsResponse(BaseModel):
    """Schema for quick stats response."""
    today: Dict[str, Any]
    active_sessions: int


# API Request schemas
class UserSearchRequest(BaseModel):
    """Schema for user search requests."""
    search: Optional[str] = Field(None, description="Search term")
    status: Optional[str] = Field(None, description="User status filter")
    role: Optional[str] = Field(None, description="User role filter")
    page: int = Field(1, description="Page number", ge=1)
    per_page: int = Field(20, description="Items per page", ge=1, le=100)


class HouseholdSearchRequest(BaseModel):
    """Schema for household search requests."""
    search: Optional[str] = Field(None, description="Search term")
    status: Optional[str] = Field(None, description="Household status filter")
    page: int = Field(1, description="Page number", ge=1)
    per_page: int = Field(20, description="Items per page", ge=1, le=100)


class ExpenseSearchRequest(BaseModel):
    """Schema for expense search requests."""
    search: Optional[str] = Field(None, description="Search term")
    household_id: Optional[str] = Field(None, description="Household ID filter")
    category: Optional[str] = Field(None, description="Category filter")
    date_from: Optional[datetime] = Field(None, description="Start date filter")
    date_to: Optional[datetime] = Field(None, description="End date filter")
    min_amount: Optional[float] = Field(None, description="Minimum amount filter")
    max_amount: Optional[float] = Field(None, description="Maximum amount filter")
    page: int = Field(1, description="Page number", ge=1)
    per_page: int = Field(20, description="Items per page", ge=1, le=100)


# Response schemas for list views
class UserListResponse(BaseModel):
    """Schema for user list response."""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    is_active: bool = Field(..., description="User active status")
    is_admin: bool = Field(..., description="User admin status")
    created_at: datetime = Field(..., description="User creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")


class HouseholdListResponse(BaseModel):
    """Schema for household list response."""
    id: str = Field(..., description="Household ID")
    name: str = Field(..., description="Household name")
    description: Optional[str] = Field(None, description="Household description")
    is_active: bool = Field(..., description="Household active status")
    member_count: int = Field(..., description="Number of household members")
    expense_count: int = Field(..., description="Number of household expenses")
    total_expenses: float = Field(..., description="Total household expense amount")
    created_at: datetime = Field(..., description="Household creation timestamp")


class ExpenseListResponse(BaseModel):
    """Schema for expense list response."""
    id: str = Field(..., description="Expense ID")
    title: str = Field(..., description="Expense title")
    amount: float = Field(..., description="Expense amount")
    currency: str = Field(..., description="Expense currency")
    description: Optional[str] = Field(None, description="Expense description")
    expense_date: datetime = Field(..., description="Expense date")
    category_name: Optional[str] = Field(None, description="Expense category name")
    household_name: str = Field(..., description="Associated household name")
    creator_name: str = Field(..., description="Expense creator name")
    creator_email: str = Field(..., description="Expense creator email")
    created_at: datetime = Field(..., description="Expense creation timestamp")


class ActivityItemResponse(BaseModel):
    """Schema for activity items."""
    type: str
    title: str
    description: str
    timestamp: Optional[datetime] = None


class AdminUserResponse(BaseModel):
    """Schema for individual user in admin interface."""
    id: str
    email: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    is_active: bool
    email_verified: bool
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    avatar_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    """Schema for paginated user list response."""
    users: List[AdminUserResponse]
    total_count: int
    page: int
    limit: int
    total_pages: int
    has_next: bool
    has_prev: bool 