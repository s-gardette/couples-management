"""
Live Updates Router

API endpoints for live updates, real-time data, and notifications.
"""

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.modules.auth.dependencies import get_current_user_from_cookie_or_header
from app.modules.live.services.live_service import LiveService
from app.modules.live.services.notification_service import NotificationService
from app.modules.live.utils.live_helpers import LiveHelpers

logger = logging.getLogger(__name__)

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Initialize router
router = APIRouter(prefix="/api/live", tags=["live"])

# Initialize services
def get_live_service() -> LiveService:
    return LiveService()

def get_notification_service() -> NotificationService:
    return NotificationService()

@router.get("/expenses", response_class=HTMLResponse)
async def get_live_expenses(
    request: Request,
    household_id: Optional[str] = None,
    search: str = "",
    category: str = "",
    date_range: str = "",
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    payment_status: str = "",
    created_by: str = "",
    sort_by: str = "date_desc",
    page: int = 1,
    per_page: int = 20,
    view_mode: str = "cards",
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Get live expenses with HTML response for HTMX."""
    try:
        # Build filters for live service
        filters = {}
        if search:
            filters['search'] = search
        if category:
            filters['category'] = category
        if date_range:
            filters['date_range'] = date_range
        if min_amount is not None:
            filters['min_amount'] = min_amount
        if max_amount is not None:
            filters['max_amount'] = max_amount
        if payment_status:
            filters['payment_status'] = payment_status
        if created_by:
            filters['created_by'] = created_by

        # Get live expense data
        live_service_instance = get_live_service()
        expense_data = await live_service_instance.get_live_expenses(
            user_id=current_user.id,
            household_id=household_id,
            filters=filters,
            sort_by=sort_by,
            page=page,
            per_page=per_page
        )
        
        # Format expenses for template
        formatted_expenses = []
        for expense in expense_data.get('expenses', []):
            # Format the expense data properly
            formatted_expense = {
                'id': expense.get('id', ''),
                'title': expense.get('title', ''),
                'amount': expense.get('amount', 0),
                'description': expense.get('description', ''),
                'date': expense.get('date', ''),
                'date_display': expense.get('date_display', ''),
                'category': expense.get('category', 'Other'),
                'payment_status': expense.get('payment_status', 'unpaid'),
                'created_by': expense.get('created_by', {})
            }
            formatted_expenses.append(formatted_expense)

        # Calculate pagination
        total_expenses = expense_data.get('total', 0)
        total_pages = (total_expenses + per_page - 1) // per_page if total_expenses > 0 else 1
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total_expenses,
            'total_pages': total_pages,
            'has_previous': page > 1,
            'has_next': page < total_pages
        }

        # Prepare template context
        context = {
            'request': request,
            'expenses': formatted_expenses,
            'view_mode': view_mode,
            'household_id': household_id,
            'pagination': pagination,
            'current_user': current_user
        }

        # Set custom headers for HTMX
        response = templates.TemplateResponse(
            "partials/expenses/live_list.html", 
            context
        )
        response.headers["X-Total-Count"] = str(total_expenses)
        response.headers["X-Live-Update"] = "true"
        
        return response

    except Exception as e:
        logger.error(f"Error getting live expenses: {e}")
        return HTMLResponse(
            content=f"<div class='text-red-500 p-4'>Error loading expenses: {str(e)}</div>",
            status_code=500
        )


@router.get("/balances")
async def get_live_balances(
    household_id: Optional[str] = None,
    current_user = Depends(get_current_user_from_cookie_or_header),
    live_service: LiveService = Depends(get_live_service)
):
    """Get live balance data with real-time calculations."""
    try:
        result = await live_service.get_live_balances(
            household_id=household_id,
            current_user_id=current_user.id
        )
        
        return LiveHelpers.format_live_response(
            data=result,
            success=result.get("success", True),
            message=result.get("message", "")
        )
        
    except Exception as e:
        logger.error(f"Error getting live balances: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_live_stats(
    household_id: Optional[str] = None,
    current_user = Depends(get_current_user_from_cookie_or_header),
    live_service: LiveService = Depends(get_live_service)
):
    """Get live summary statistics for the household."""
    try:
        result = await live_service.get_live_stats(
            household_id=household_id,
            current_user_id=current_user.id
        )
        
        return LiveHelpers.format_live_response(
            data=result,
            success=result.get("success", True),
            message=result.get("message", "")
        )
        
    except Exception as e:
        logger.error(f"Error getting live stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/expense/{expense_id}")
async def get_live_expense_details(
    expense_id: UUID,
    current_user = Depends(get_current_user_from_cookie_or_header),
    live_service: LiveService = Depends(get_live_service)
):
    """Get live expense details with real-time data."""
    try:
        result = await live_service.get_live_expense_details(
            expense_id=expense_id,
            current_user_id=current_user.id
        )
        
        return LiveHelpers.format_live_response(
            data=result,
            success=result.get("success", True),
            message=result.get("message", "")
        )
        
    except Exception as e:
        logger.error(f"Error getting live expense details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-update")
async def trigger_live_update(
    component: str = Form("expenses"),
    data: Optional[str] = Form(None),
    current_user = Depends(get_current_user_from_cookie_or_header),
    live_service: LiveService = Depends(get_live_service)
):
    """Trigger a live update event."""
    try:
        result = await live_service.trigger_update(
            component=component,
            data=data,
            user_id=current_user.id
        )
        
        return LiveHelpers.format_live_response(
            data=result,
            success=result.get("success", True),
            message=result.get("message", "")
        )
        
    except Exception as e:
        logger.error(f"Error triggering live update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications")
async def get_notifications(
    current_user = Depends(get_current_user_from_cookie_or_header),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Get pending notifications for the current user."""
    try:
        notifications = notification_service.get_user_notifications(
            user_id=str(current_user.id)
        )
        
        return LiveHelpers.format_live_response(
            data={"notifications": notifications},
            success=True,
            message="Notifications retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications")
async def create_notification(
    message: str = Form(...),
    notification_type: str = Form("info"),
    duration: Optional[int] = Form(None),
    current_user = Depends(get_current_user_from_cookie_or_header),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Create a new notification."""
    try:
        notification_id = notification_service.create_notification(
            message=message,
            type=notification_type,
            duration=duration,
            user_id=str(current_user.id)
        )
        
        return LiveHelpers.format_live_response(
            data={"notification_id": notification_id},
            success=True,
            message="Notification created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notifications/{notification_id}")
async def dismiss_notification(
    notification_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Dismiss a specific notification."""
    try:
        success = notification_service.dismiss_notification(
            notification_id=notification_id,
            user_id=str(current_user.id)
        )
        
        return LiveHelpers.format_live_response(
            data={"dismissed": success},
            success=success,
            message="Notification dismissed" if success else "Notification not found"
        )
        
    except Exception as e:
        logger.error(f"Error dismissing notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notifications")
async def clear_all_notifications(
    current_user = Depends(get_current_user_from_cookie_or_header),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Clear all notifications."""
    try:
        count = notification_service.clear_all_notifications(
            user_id=str(current_user.id)
        )
        
        return LiveHelpers.format_live_response(
            data={"cleared_count": count},
            success=True,
            message=f"Cleared {count} notifications"
        )
        
    except Exception as e:
        logger.error(f"Error clearing notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/toast")
async def create_toast_notification(
    message: str = Form(...),
    type: str = Form("info"),
    duration: Optional[int] = Form(None),
    current_user = Depends(get_current_user_from_cookie_or_header),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Create a new notification."""
    try:
        notification_id = notification_service.create_toast(
            message=message,
            type=type,
            duration=duration,
            user_id=str(current_user.id)
        )
        
        return LiveHelpers.format_live_response(
            data={"notification_id": notification_id},
            success=True,
            message="Notification created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating toast notification: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 