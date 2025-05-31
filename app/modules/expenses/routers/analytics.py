"""
Analytics router for expense analytics and reporting.
"""

import logging
from datetime import datetime, date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models.user import User
from app.modules.expenses.schemas.analytics import (
    SpendingSummaryResponse,
    CategoryAnalysisResponse,
    UserSpendingPatternsResponse,
    HouseholdBalancesResponse,
    AnalyticsDashboardResponse,
    ExportDataResponse
)
from app.modules.expenses.services.analytics_service import AnalyticsService
from app.modules.expenses.services.household_service import HouseholdService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/households/{household_id}/analytics", tags=["analytics"])


def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    """Get analytics service instance."""
    return AnalyticsService(db)


def get_household_service(db: Session = Depends(get_db)) -> HouseholdService:
    """Get household service instance."""
    return HouseholdService(db)


async def verify_household_access(
    household_id: UUID,
    current_user: User,
    household_service: HouseholdService
):
    """Verify user has access to household."""
    has_permission = await household_service.check_user_permission(
        user_id=current_user.id,
        household_id=household_id
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this household"
        )


@router.get("/summary", response_model=SpendingSummaryResponse)
async def get_spending_summary(
    household_id: UUID,
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    category_ids: Optional[str] = Query(None, description="Filter by category IDs (comma-separated)"),
    user_ids: Optional[str] = Query(None, description="Filter by user IDs (comma-separated)"),
    include_inactive: bool = Query(False, description="Include inactive expenses"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Get spending summary analytics for a household."""
    try:
        await verify_household_access(household_id, current_user, household_service)
        
        success, message, summary = await analytics_service.get_spending_summary(
            household_id=household_id,
            user_id=current_user.id,
            start_date=date_from,
            end_date=date_to
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting spending summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve spending summary"
        )


@router.get("/categories", response_model=List[CategoryAnalysisResponse])
async def get_category_analysis(
    household_id: UUID,
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    limit: int = Query(10, ge=1, le=50, description="Number of top categories to return"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Get category analysis for a household."""
    try:
        await verify_household_access(household_id, current_user, household_service)
        
        success, message, analysis = await analytics_service.get_category_analysis(
            household_id=household_id,
            user_id=current_user.id,
            start_date=date_from,
            end_date=date_to
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Return the categories list, limited by the limit parameter
        categories = analysis.get("categories", [])
        return categories[:limit]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category analysis"
        )


@router.get("/users", response_model=List[UserSpendingPatternsResponse])
async def get_user_spending_patterns(
    household_id: UUID,
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    user_id: Optional[UUID] = Query(None, description="Specific user to analyze"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Get user spending patterns for a household."""
    try:
        await verify_household_access(household_id, current_user, household_service)
        
        success, message, patterns = await analytics_service.get_user_spending_patterns(
            household_id=household_id,
            user_id=current_user.id,
            target_user_id=user_id,
            start_date=date_from,
            end_date=date_to
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Convert patterns dict to list format expected by response model
        if isinstance(patterns, dict):
            return [patterns]
        return patterns
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user spending patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user spending patterns"
        )


@router.get("/balances", response_model=HouseholdBalancesResponse)
async def get_household_balances(
    household_id: UUID,
    include_settled: bool = Query(False, description="Include settled balances"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Get balance calculations and settlement suggestions for a household."""
    try:
        await verify_household_access(household_id, current_user, household_service)
        
        success, message, balances = await analytics_service.get_balance_calculations(
            household_id=household_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return balances
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting household balances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve household balances"
        )


@router.get("/export", response_model=ExportDataResponse)
async def export_household_data(
    household_id: UUID,
    format: str = Query("csv", description="Export format: csv, json, excel"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    include_categories: bool = Query(True, description="Include category data"),
    include_users: bool = Query(True, description="Include user data"),
    include_balances: bool = Query(True, description="Include balance data"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Export household data in various formats."""
    try:
        await verify_household_access(household_id, current_user, household_service)
        
        if format not in ["csv", "json", "excel"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format must be one of: csv, json, excel"
            )
        
        success, message, export_data = await analytics_service.export_data(
            household_id=household_id,
            user_id=current_user.id,
            export_type=format,
            start_date=date_from,
            end_date=date_to,
            include_shares=True
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return export_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting household data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export household data"
        )


@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
async def get_analytics_dashboard(
    household_id: UUID,
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Get comprehensive analytics dashboard data for a household."""
    try:
        await verify_household_access(household_id, current_user, household_service)
        
        # Get all analytics data in parallel
        import asyncio
        
        spending_summary_task = analytics_service.get_spending_summary(
            household_id=household_id,
            user_id=current_user.id,
            start_date=date_from,
            end_date=date_to
        )
        
        category_analysis_task = analytics_service.get_category_analysis(
            household_id=household_id,
            user_id=current_user.id,
            start_date=date_from,
            end_date=date_to
        )
        
        user_patterns_task = analytics_service.get_user_spending_patterns(
            household_id=household_id,
            user_id=current_user.id,
            start_date=date_from,
            end_date=date_to
        )
        
        balance_overview_task = analytics_service.get_balance_calculations(
            household_id=household_id,
            user_id=current_user.id
        )
        
        # Wait for all tasks to complete
        results = await asyncio.gather(
            spending_summary_task,
            category_analysis_task,
            user_patterns_task,
            balance_overview_task
        )
        
        # Unpack results and check for errors
        spending_success, spending_msg, spending_summary = results[0]
        category_success, category_msg, category_analysis = results[1]
        user_success, user_msg, user_patterns = results[2]
        balance_success, balance_msg, balance_overview = results[3]
        
        if not spending_success:
            raise HTTPException(status_code=400, detail=f"Spending summary error: {spending_msg}")
        if not category_success:
            raise HTTPException(status_code=400, detail=f"Category analysis error: {category_msg}")
        if not user_success:
            raise HTTPException(status_code=400, detail=f"User patterns error: {user_msg}")
        if not balance_success:
            raise HTTPException(status_code=400, detail=f"Balance overview error: {balance_msg}")
        
        # Get household info
        household = await household_service.get_household_with_members(household_id)
        if not household:
            raise HTTPException(status_code=404, detail="Household not found")
        
        # Get top categories (limit to 5 for dashboard)
        top_categories = category_analysis.get("categories", [])[:5]
        
        # Generate insights and recommendations
        key_insights = []
        recommendations = []
        alerts = []
        
        # Add some basic insights based on the data
        total_expenses = spending_summary.get("totals", {}).get("expense_count", 0)
        total_amount = spending_summary.get("totals", {}).get("total_amount", 0)
        
        if total_expenses > 0:
            key_insights.append(f"Total of {total_expenses} expenses recorded")
            key_insights.append(f"Total spending: ${total_amount:.2f}")
        
        if top_categories:
            key_insights.append(f"Top spending category: {top_categories[0].get('name', 'Unknown')}")
        
        total_outstanding = balance_overview.get("total_outstanding", 0)
        if total_outstanding > 0:
            alerts.append(f"Outstanding balances: ${total_outstanding:.2f}")
            recommendations.append("Consider settling outstanding balances")
        
        return AnalyticsDashboardResponse(
            household_id=household_id,
            household_name=household.name,
            generated_at=datetime.utcnow(),
            spending_summary=spending_summary,
            top_categories=top_categories,
            user_patterns=user_patterns if isinstance(user_patterns, list) else [user_patterns],
            balance_overview=balance_overview,
            key_insights=key_insights,
            recommendations=recommendations,
            alerts=alerts
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics dashboard"
        ) 