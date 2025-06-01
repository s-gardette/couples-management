"""
Live Updates Router

API endpoints for live updates, real-time data, and notifications.
"""

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Form, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models.user import User
from app.modules.live.services.live_service import LiveService
from app.modules.live.services.notification_service import NotificationService
from app.modules.live.utils.live_helpers import LiveHelpers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/live", tags=["live"])

# Initialize services
def get_live_service(db: Session = Depends(get_db)) -> LiveService:
    return LiveService(db)

def get_notification_service() -> NotificationService:
    return NotificationService()


@router.get("/expenses")
async def get_live_expenses(
    household_id: UUID,
    search: Optional[str] = None,
    category: Optional[str] = None,
    date_range: Optional[str] = None,
    payment_status: Optional[str] = None,
    created_by: Optional[str] = None,
    sort_by: Optional[str] = "date_desc",
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    view_mode: Optional[str] = "cards",
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    live_service: LiveService = Depends(get_live_service)
):
    """Get live expense data with real-time updates."""
    try:
        # Build filters
        filters = {
            "search": search,
            "category": category,
            "date_range": date_range,
            "payment_status": payment_status,
            "created_by": created_by,
            "sort_by": sort_by,
            "min_amount": min_amount,
            "max_amount": max_amount
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        result = await live_service.get_live_expenses(
            household_id=household_id,
            current_user_id=current_user.id,
            filters=filters,
            view_mode=view_mode,
            page=page,
            per_page=per_page
        )
        
        return LiveHelpers.format_live_response(
            data=result,
            success=result.get("success", True),
            message=result.get("message", ""),
            meta={
                "view_mode": view_mode,
                "filters": filters,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": result.get("total", 0),
                    "total_pages": result.get("total_pages", 0)
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting live expenses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balances")
async def get_live_balances(
    household_id: UUID,
    current_user: User = Depends(get_current_user),
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
    household_id: UUID,
    current_user: User = Depends(get_current_user),
    live_service: LiveService = Depends(get_live_service)
):
    """Get live summary statistics for the household."""
    try:
        result = await live_service.get_live_summary_stats(
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
    current_user: User = Depends(get_current_user),
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
    update_type: str = Form(...),
    household_id: UUID = Form(...),
    data: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    live_service: LiveService = Depends(get_live_service)
):
    """Trigger a live update event."""
    try:
        import json
        
        # Parse data if provided
        update_data = None
        if data:
            try:
                update_data = json.loads(data)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON data")
        
        success = live_service.trigger_live_update(
            update_type=update_type,
            household_id=household_id,
            data=update_data
        )
        
        return LiveHelpers.format_live_response(
            data={"triggered": success},
            success=success,
            message="Live update triggered successfully" if success else "Failed to trigger live update"
        )
        
    except Exception as e:
        logger.error(f"Error triggering live update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications")
async def get_notifications(
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Get pending notifications for the current user."""
    try:
        notifications = notification_service.get_pending_notifications()
        context = notification_service.get_notification_context()
        
        return LiveHelpers.format_live_response(
            data={
                "notifications": notifications,
                "context": context
            },
            success=True,
            message=""
        )
        
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications")
async def create_notification(
    message: str = Form(...),
    notification_type: str = Form("info"),
    duration: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Create a new notification."""
    try:
        from app.modules.live.services.notification_service import NotificationType
        
        # Validate notification type
        try:
            notif_type = NotificationType(notification_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid notification type")
        
        notification = notification_service.create_notification(
            message=message,
            notification_type=notif_type,
            duration=duration
        )
        
        return LiveHelpers.format_live_response(
            data=notification,
            success=True,
            message="Notification created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notifications/{notification_id}")
async def dismiss_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Dismiss a specific notification."""
    try:
        success = notification_service.dismiss_notification(notification_id)
        
        return LiveHelpers.format_live_response(
            data={"dismissed": success},
            success=success,
            message="Notification dismissed successfully" if success else "Notification not found"
        )
        
    except Exception as e:
        logger.error(f"Error dismissing notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notifications")
async def clear_all_notifications(
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Clear all notifications."""
    try:
        count = notification_service.clear_all_notifications()
        
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
    notification_type: str = Form("info"),
    duration: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """Create a toast notification for immediate display."""
    try:
        toast = LiveHelpers.create_toast_notification(
            message=message,
            notification_type=notification_type,
            duration=duration
        )
        
        return LiveHelpers.format_live_response(
            data=toast,
            success=True,
            message="Toast notification created"
        )
        
    except Exception as e:
        logger.error(f"Error creating toast notification: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 