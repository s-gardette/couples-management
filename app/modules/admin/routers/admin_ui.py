"""
Admin UI routes for web interface (Jinja2/HTMX/Alpine).
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from sqlalchemy.orm import Session

from app.modules.admin.dependencies import require_admin_auth, require_admin_permission, check_admin_permission
from app.modules.admin.services import AdminDashboardService, AdminUsersService
from app.modules.auth.models.user import User
from app.database import get_db
from app.config import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/admin", tags=["admin-ui"])

# Setup Enhanced Jinja2 templates with automatic global context
from app.core.templates import templates


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    admin_user: User = Depends(require_admin_auth)  # Use basic auth for dashboard
):
    """
    Admin dashboard - main entry point for admin interface.
    Basic admin authentication required.
    """
    logger.info(f"Admin dashboard accessed by {admin_user.email}")
    
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "current_user": admin_user,
            "page_title": "Admin Dashboard",
            "admin_section": "dashboard"
        }
    )


@router.get("/unauthorized", response_class=HTMLResponse)
async def admin_unauthorized(request: Request):
    """
    Admin unauthorized page - shown when user lacks admin privileges.
    """
    return templates.TemplateResponse(
        request,
        "admin/unauthorized.html",
        {
            "page_title": "Access Denied - Admin",
            "admin_contact_email": settings.admin_contact_email
        }
    )


# API endpoints for dashboard data
@router.get("/api/system-overview")
async def get_system_overview(
    request: Request,
    admin_user: User = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """
    API endpoint for system overview data.
    """
    # Check specific permission
    if not check_admin_permission(admin_user, 'system.settings'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: system.settings"
        )
    
    dashboard_service = AdminDashboardService(db)
    overview = await dashboard_service.get_system_overview()
    
    # Return as HTML for HTMX
    return templates.TemplateResponse(
        request,
        "partials/admin/system_overview.html",
        {
            "overview": overview
        }
    )


@router.get("/api/system-health")
async def get_system_health(
    request: Request,
    admin_user: User = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """
    API endpoint for system health data.
    """
    # Check specific permission
    if not check_admin_permission(admin_user, 'system.settings'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: system.settings"
        )
    
    dashboard_service = AdminDashboardService(db)
    health = await dashboard_service.get_system_health()
    
    # Return as HTML for HTMX
    return templates.TemplateResponse(
        request,
        "partials/admin/system_health.html",
        {
            "health": health
        }
    )


@router.get("/api/recent-activity")
async def get_recent_activity(
    request: Request,
    admin_user: User = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """
    API endpoint for recent activity data.
    """
    # Check specific permission
    if not check_admin_permission(admin_user, 'users.view'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: users.view"
        )
    
    dashboard_service = AdminDashboardService(db)
    activities = await dashboard_service.get_recent_activity(limit=10)
    
    # Return as HTML for HTMX
    return templates.TemplateResponse(
        request,
        "partials/admin/recent_activity.html",
        {
            "activities": activities
        }
    )


@router.get("/api/quick-stats")
async def get_quick_stats(
    request: Request,
    admin_user: User = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """
    API endpoint for quick stats data.
    """
    # Check specific permission
    if not check_admin_permission(admin_user, 'users.view'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: users.view"
        )
    
    dashboard_service = AdminDashboardService(db)
    stats = await dashboard_service.get_quick_stats()
    
    # Return as HTML for HTMX
    return templates.TemplateResponse(
        request,
        "partials/admin/quick_stats.html",
        {
            "stats": stats
        }
    )


# User Management Routes
@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    admin_user: User = Depends(require_admin_auth),  # Use basic auth first
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None),
    role_filter: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    User management interface.
    Admin authentication required.
    """
    # Check specific permission after getting user
    if not check_admin_permission(admin_user, 'users.view'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: users.view"
        )
    
    logger.info(f"Admin users page accessed by {admin_user.email}")
    
    users_service = AdminUsersService(db)
    users_data = await users_service.get_users_list(
        search=search,
        role_filter=role_filter,
        status_filter=status_filter,
        page=page,
        limit=limit
    )
    
    return templates.TemplateResponse(
        request,
        "admin/users/list.html",
        {
            "current_user": admin_user,
            "page_title": "User Management",
            "admin_section": "users",
            "users_data": users_data,
            "search": search or "",
            "role_filter": role_filter or "",
            "status_filter": status_filter or ""
        }
    )


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(
    request: Request,
    user_id: str,
    admin_user: User = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """
    Edit user form interface.
    """
    # Check specific permission
    if not check_admin_permission(admin_user, 'users.edit'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: users.edit"
        )
    
    logger.info(f"Admin edit user {user_id} accessed by {admin_user.email}")
    
    users_service = AdminUsersService(db)
    user_data = await users_service.get_user_by_id(user_id)
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return templates.TemplateResponse(
        request,
        "admin/users/edit.html",
        {
            "current_user": admin_user,
            "page_title": f"Edit User - {user_data.email}",
            "admin_section": "users",
            "user": user_data
        }
    )


@router.post("/users/{user_id}/edit")
async def edit_user_submit(
    request: Request,
    user_id: str,
    admin_user: User = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """
    Process user edit form submission.
    """
    # Check specific permission
    if not check_admin_permission(admin_user, 'users.edit'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: users.edit"
        )
    
    logger.info(f"Admin editing user {user_id} by {admin_user.email}")
    
    # Parse form data
    form_data = await request.form()
    
    users_service = AdminUsersService(db)
    result = await users_service.update_user(
        user_id=user_id,
        admin_user_id=str(admin_user.id),
        first_name=form_data.get("first_name"),
        last_name=form_data.get("last_name"),
        username=form_data.get("username"),
        email=form_data.get("email"),
        role=form_data.get("role"),
        is_active=form_data.get("is_active") == "on",
        email_verified=form_data.get("email_verified") == "on"
    )
    
    if result["success"]:
        # Check if this is an AJAX request (fetch with Authorization header)
        auth_header = request.headers.get("authorization")
        is_ajax = auth_header and auth_header.startswith("Bearer ")
        
        if is_ajax:
            # For AJAX requests, return JSON
            return JSONResponse({
                "success": True,
                "message": "User updated successfully",
                "redirect_url": "/admin/users"
            })
        else:
            # For traditional form submissions, use redirect
            return RedirectResponse(
                url="/admin/users?message=User updated successfully",
                status_code=302
            )
    else:
        # Check if this is an AJAX request
        auth_header = request.headers.get("authorization")
        is_ajax = auth_header and auth_header.startswith("Bearer ")
        
        if is_ajax:
            # For AJAX requests, return JSON error
            return JSONResponse({
                "success": False,
                "message": result["message"]
            }, status_code=400)
        else:
            # For traditional form submissions, redisplay form with error
            user_data = await users_service.get_user_by_id(user_id)
            return templates.TemplateResponse(
                request,
                "admin/users/edit.html",
                {
                    "current_user": admin_user,
                    "page_title": f"Edit User - {user_data.email}",
                    "admin_section": "users",
                    "user": user_data,
                    "error_message": result["message"]
                }
            )


@router.get("/api/users/search")
async def search_users(
    request: Request,
    admin_user: User = Depends(require_admin_auth),
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None),
    role_filter: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Search and filter users with HTMX.
    """
    # Check specific permission
    if not check_admin_permission(admin_user, 'users.view'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: users.view"
        )
    
    users_service = AdminUsersService(db)
    users_data = await users_service.get_users_list(
        search=search,
        role_filter=role_filter,
        status_filter=status_filter,
        page=page,
        limit=limit
    )
    
    return templates.TemplateResponse(
        request,
        "partials/admin/users_table.html",
        {
            "users_data": users_data,
            "current_user": admin_user,
            "search": search or "",
            "role_filter": role_filter or "",
            "status_filter": status_filter or ""
        }
    )


@router.get("/api/users/{user_id}")
async def get_user_details(
    request: Request,
    user_id: str,
    admin_user: User = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """
    Get detailed user information for viewing.
    """
    # Check specific permission
    if not check_admin_permission(admin_user, 'users.view'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: users.view"
        )
    
    users_service = AdminUsersService(db)
    user_data = await users_service.get_user_by_id(user_id)
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return templates.TemplateResponse(
        request,
        "partials/admin/user_details.html",
        {
            "user": user_data,
            "current_admin": admin_user
        }
    )


@router.post("/api/users/{user_id}/toggle-status")
async def toggle_user_status(
    request: Request,
    user_id: str,
    admin_user: User = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """
    Toggle user active status (activate/deactivate).
    """
    # Check specific permission
    if not check_admin_permission(admin_user, 'users.edit'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: users.edit"
        )
    
    users_service = AdminUsersService(db)
    result = await users_service.toggle_user_status(user_id, str(admin_user.id))
    
    if result["success"]:
        # Return updated status HTML for HTMX
        is_active = result["new_status"]
        status_html = f"""
        <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full 
            {'bg-green-100 text-green-800' if is_active else 'bg-red-100 text-red-800'}">
            {'Active' if is_active else 'Inactive'}
        </span>
        """
        return HTMLResponse(content=status_html, status_code=200)
    else:
        return JSONResponse(
            status_code=400,
            content=result
        )


# Placeholder routes for other admin sections
@router.get("/households", response_class=HTMLResponse)
async def admin_households(
    request: Request,
    admin_user: User = Depends(require_admin_auth)
):
    """
    Household management interface.
    """
    logger.info(f"Admin households page accessed by {admin_user.email}")
    
    return templates.TemplateResponse(
        request,
        "admin/households/list.html",
        {
            "current_user": admin_user,
            "page_title": "Household Management",
            "admin_section": "households"
        }
    )


@router.get("/expenses", response_class=HTMLResponse)
async def admin_expenses(
    request: Request,
    admin_user: User = Depends(require_admin_auth),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    household_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """
    Expense management interface.
    """
    from app.modules.expenses.models.expense import Expense
    from app.modules.expenses.models.household import Household
    from app.modules.expenses.models.category import Category
    from app.modules.expenses.models.expense_share import ExpenseShare
    from app.modules.expenses.models.user_household import UserHousehold
    from sqlalchemy.orm import joinedload
    from sqlalchemy import desc, or_, and_, func
    from datetime import datetime, date
    from decimal import Decimal
    
    logger.info(f"Admin expenses page accessed by {admin_user.email}")
    
    try:
        
        # Build base query for all expenses (admin can see everything)
        query = (
            db.query(Expense)
            .options(
                joinedload(Expense.category),
                joinedload(Expense.creator),
                joinedload(Expense.household),
                joinedload(Expense.shares).joinedload(ExpenseShare.user_household).joinedload(UserHousehold.user)
            )
            .filter(Expense.is_active == True)
        )
        
        # Apply filters
        if search:
            query = query.filter(
                or_(
                    Expense.title.ilike(f"%{search}%"),
                    Expense.description.ilike(f"%{search}%")
                )
            )
        
        if category:
            query = query.join(Category).filter(Category.name.ilike(f"%{category}%"))
        
        if household_id:
            query = query.filter(Expense.household_id == household_id)
        
        if date_from:
            try:
                start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(Expense.expense_date >= start_date)
            except ValueError:
                pass  # Ignore invalid date format
        
        if date_to:
            try:
                end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
                query = query.filter(Expense.expense_date <= end_date)
            except ValueError:
                pass  # Ignore invalid date format
        
        # Get total count for pagination
        total_expenses = query.count()
        
        # Apply pagination and sorting
        expenses = (
            query.order_by(desc(Expense.expense_date))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        
        # Calculate statistics
        stats_query = db.query(
            func.count(Expense.id).label('total_count'),
            func.sum(Expense.amount).label('total_amount')
        ).filter(Expense.is_active == True)
        
        stats = stats_query.first()
        
        # Calculate this month's stats separately
        this_month_start = date.today().replace(day=1)
        this_month_query = db.query(
            func.count(Expense.id).label('count'),
            func.sum(Expense.amount).label('amount')
        ).filter(
            Expense.is_active == True,
            Expense.expense_date >= this_month_start
        )
        this_month_stats = this_month_query.first()
        
        # Calculate paid vs unpaid
        paid_query = db.query(func.sum(Expense.amount)).join(ExpenseShare).filter(
            Expense.is_active == True,
            ExpenseShare.is_active == True,
            ExpenseShare.is_paid == True
        )
        paid_amount = paid_query.scalar() or Decimal('0')
        
        # Get all households for filter dropdown
        households = db.query(Household).filter(Household.is_active == True).all()
        
        # Format expenses for template
        formatted_expenses = []
        for expense in expenses:
            # Calculate payment status
            if expense.shares:
                paid_shares = sum(1 for share in expense.shares if share.is_paid and share.is_active)
                total_shares = sum(1 for share in expense.shares if share.is_active)
                if paid_shares == total_shares and total_shares > 0:
                    payment_status = "paid"
                elif paid_shares > 0:
                    payment_status = "partial"
                else:
                    payment_status = "unpaid"
            else:
                payment_status = "unpaid"
            
            formatted_expense = {
                "id": str(expense.id),
                "title": expense.title,
                "amount": float(expense.amount),
                "description": expense.description or "",
                "date": expense.expense_date.strftime('%Y-%m-%d'),
                "date_display": expense.expense_date.strftime('%b %d, %Y'),
                "category": expense.category.name if expense.category else "Other",
                "household": {
                    "id": str(expense.household.id),
                    "name": expense.household.name
                } if expense.household else None,
                "created_by": {
                    "username": expense.creator.username if expense.creator else "Unknown",
                    "first_name": expense.creator.first_name if expense.creator else "Unknown",
                    "last_name": expense.creator.last_name if expense.creator else "User"
                },
                "payment_status": payment_status
            }
            formatted_expenses.append(formatted_expense)
        
        # Calculate pagination
        total_pages = (total_expenses + per_page - 1) // per_page
        
        return templates.TemplateResponse(
            request,
            "admin/expenses/list.html",
            {
                "current_user": admin_user,
                "page_title": "Expense Management",
                "admin_section": "expenses",
                "expenses": formatted_expenses,
                "households": households,
                "stats": {
                    "total_expenses": stats.total_count or 0,
                    "total_amount": float(stats.total_amount or 0),
                    "this_month_count": this_month_stats.count or 0,
                    "this_month_amount": float(this_month_stats.amount or 0),
                    "paid_amount": float(paid_amount),
                    "unpaid_amount": float((stats.total_amount or 0) - paid_amount)
                },
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_expenses,
                    "total_pages": total_pages,
                    "has_previous": page > 1,
                    "has_next": page < total_pages
                },
                "filters": {
                    "search": search or "",
                    "category": category or "",
                    "household_id": household_id or "",
                    "date_from": date_from or "",
                    "date_to": date_to or ""
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading admin expenses: {e}")
        return templates.TemplateResponse(
            request,
            "admin/expenses/list.html",
            {
                "current_user": admin_user,
                "page_title": "Expense Management",
                "admin_section": "expenses",
                "expenses": [],
                "households": [],
                "stats": {
                    "total_expenses": 0,
                    "total_amount": 0,
                    "this_month_count": 0,
                    "this_month_amount": 0,
                    "paid_amount": 0,
                    "unpaid_amount": 0
                },
                "pagination": {
                    "page": 1,
                    "per_page": per_page,
                    "total": 0,
                    "total_pages": 1,
                    "has_previous": False,
                    "has_next": False
                },
                "filters": {
                    "search": "",
                    "category": "",
                    "household_id": "",
                    "date_from": "",
                    "date_to": ""
                },
                "error": "Failed to load expenses"
            }
        )


@router.get("/analytics", response_class=HTMLResponse)
async def admin_analytics(
    request: Request,
    admin_user: User = Depends(require_admin_auth)
):
    """
    Analytics interface.
    """
    # Check specific permission
    if not check_admin_permission(admin_user, 'system.logs'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: system.logs"
        )
    
    logger.info(f"Admin analytics page accessed by {admin_user.email}")
    
    return templates.TemplateResponse(
        request,
        "admin/analytics.html",
        {
            "current_user": admin_user,
            "page_title": "Analytics",
            "admin_section": "analytics"
        }
    )


@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(
    request: Request,
    admin_user: User = Depends(require_admin_auth)
):
    """
    Admin settings interface.
    """
    # Check specific permission
    if not check_admin_permission(admin_user, 'system.settings'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: system.settings"
        )
    
    logger.info(f"Admin settings page accessed by {admin_user.email}")
    
    return templates.TemplateResponse(
        request,
        "admin/settings.html",
        {
            "current_user": admin_user,
            "page_title": "Admin Settings",
            "admin_section": "settings"
        }
    )


@router.post("/users/{user_id}/change-password")
async def change_user_password(
    request: Request,
    user_id: str,
    admin_user: User = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """
    Change a user's password (admin only).
    """
    # Check specific permission
    if not check_admin_permission(admin_user, 'users.password'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: users.password"
        )
    
    try:
        # Parse form data
        form_data = await request.form()
        new_password = form_data.get("new_password")
        force_change = form_data.get("force_change") == "on"
        
        if not new_password:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Password is required"}
            )
        
        # Use service to change password
        users_service = AdminUsersService(db)
        result = await users_service.change_user_password(
            user_id=user_id,
            new_password=new_password,
            force_change_on_next_login=force_change,
            admin_user_id=str(admin_user.id)
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error changing password for user {user_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "An error occurred while changing the password"}
        )


@router.post("/users/{user_id}/send-reset-link")
async def send_password_reset_link(
    request: Request,
    user_id: str,
    admin_user: User = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """
    Send password reset link to user.
    """
    # Check specific permission
    if not check_admin_permission(admin_user, 'users.password'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: users.password"
        )
    
    try:
        users_service = AdminUsersService(db)
        result = await users_service.send_password_reset_link(
            user_id=user_id,
            admin_user_id=str(admin_user.id)
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error sending reset link for user {user_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "An error occurred while sending the reset link"}
        ) 