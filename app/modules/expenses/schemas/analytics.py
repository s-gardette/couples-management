"""
Pydantic schemas for analytics-related API endpoints.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AnalyticsFilters(BaseModel):
    """Schema for analytics filtering parameters."""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    category_ids: Optional[List[UUID]] = None
    user_ids: Optional[List[UUID]] = None
    include_inactive: bool = Field(default=False, description="Include inactive expenses")


class PeriodInfo(BaseModel):
    """Schema for period information."""
    start_date: str
    end_date: str
    period_type: str


class TotalsInfo(BaseModel):
    """Schema for totals information."""
    total_amount: float
    expense_count: int
    average_expense: float
    daily_average: float


class TrendsInfo(BaseModel):
    """Schema for trends information."""
    current_period: float
    previous_period: float
    change_amount: float
    change_percentage: float
    trend: str


class TopExpenseInfo(BaseModel):
    """Schema for top expense information."""
    id: str
    title: str
    amount: float
    date: str
    category: str
    creator: str


class SpendingSummaryResponse(BaseModel):
    """Schema for spending summary analytics."""
    period: PeriodInfo
    totals: TotalsInfo
    category_breakdown: List[Dict[str, Any]]
    user_breakdown: List[Dict[str, Any]]
    time_series: List[Dict[str, Any]]
    top_expenses: List[TopExpenseInfo]
    trends: TrendsInfo


class CategoryAnalysisResponse(BaseModel):
    """Schema for category analysis."""
    id: Optional[str] = None
    name: str
    color: str
    icon: Optional[str] = None
    total_amount: float
    expense_count: int
    average_amount: float
    percentage: float


class UserSpendingPatternsResponse(BaseModel):
    """Schema for user spending patterns."""
    # This will be a flexible dict since the service returns various formats
    model_config = ConfigDict(extra="allow")


class BalanceCalculationResponse(BaseModel):
    """Schema for balance calculations."""
    # This will be a flexible dict since the service returns various formats
    model_config = ConfigDict(extra="allow")


class HouseholdBalancesResponse(BaseModel):
    """Schema for household balance overview."""
    # This will be a flexible dict since the service returns various formats
    model_config = ConfigDict(extra="allow")


class TrendAnalysisResponse(BaseModel):
    """Schema for trend analysis."""
    period: str  # "daily", "weekly", "monthly"
    data_points: List[Dict[str, Any]]
    
    # Trend metrics
    trend_direction: str  # "increasing", "decreasing", "stable"
    growth_rate: float
    volatility: float
    
    # Predictions
    predicted_next_period: Optional[Decimal] = None
    confidence_level: Optional[float] = None


class ExportDataResponse(BaseModel):
    """Schema for data export response."""
    # This will be a flexible dict since the service returns various formats
    model_config = ConfigDict(extra="allow")


class AnalyticsDashboardResponse(BaseModel):
    """Schema for analytics dashboard overview."""
    household_id: UUID
    household_name: str
    generated_at: datetime
    
    # Summary data - using flexible dicts to match service output
    spending_summary: Dict[str, Any]
    top_categories: List[Dict[str, Any]]
    user_patterns: List[Dict[str, Any]]
    balance_overview: Dict[str, Any]
    
    # Quick insights
    key_insights: List[str]
    recommendations: List[str]
    alerts: List[str] = Field(default_factory=list) 