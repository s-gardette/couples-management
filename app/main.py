"""
Main FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from uuid import UUID
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse

from app.config import settings
from app.database import get_db
from app.core.routers import health
from app.modules.auth.routers import auth_router, users_router
from app.modules.auth.routers.admin import router as admin_router
from app.modules.auth.dependencies import require_authentication, get_current_user_optional, get_current_user_from_cookie_or_header
from app.modules.auth.utils.startup import initialize_auth_system
from app.modules.auth.schemas.admin import AdminAccessRestrictedResponse
from app.modules.expenses.routers import (
    households_router,
    expenses_router,
    categories_router,
    analytics_router,
    payments_router,
    balances_router
)
from app.modules.live.routers import live_router
from app.modules.expenses.services import HouseholdService
from app.modules.expenses.models.user_household import UserHousehold

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🚀 Starting Household Management App...")
    
    # Initialize auth system
    db = next(get_db())
    try:
        init_results = await initialize_auth_system(db)
        print(f"✅ Auth system initialized: {init_results}")
    except Exception as e:
        print(f"❌ Auth system initialization failed: {e}")
    finally:
        db.close()
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Household Management App...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Include routers with mandatory authentication
if settings.require_authentication_for_all:
    # Include auth router without global authentication dependency
    # Individual endpoints will handle their own authentication requirements
    app.include_router(auth_router, prefix="/api")
    
    # Health endpoint should always be public (no authentication required)
    app.include_router(health.router, prefix="/health", tags=["health"])
    
    # All other routes require authentication
    app.include_router(users_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(admin_router, prefix="/api", dependencies=[Depends(require_authentication)])
    
    # Expenses module routers
    app.include_router(households_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(expenses_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(categories_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(analytics_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(payments_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(balances_router, prefix="/api", dependencies=[Depends(require_authentication)])
    
    # Live updates module router
    app.include_router(live_router, dependencies=[Depends(require_authentication)])
else:
    # Normal routing (for development)
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    
    # Expenses module routers (development mode)
    app.include_router(households_router, prefix="/api")
    app.include_router(expenses_router, prefix="/api")
    app.include_router(categories_router, prefix="/api")
    app.include_router(analytics_router, prefix="/api")
    app.include_router(payments_router, prefix="/api")
    app.include_router(balances_router, prefix="/api")
    
    # Live updates module router (development mode)
    app.include_router(live_router)


# Access restricted page (only public endpoint)
@app.get("/access-restricted", response_class=HTMLResponse)
async def access_restricted(request: Request):
    """Access restricted page - only public endpoint available."""
    return templates.TemplateResponse(
        request, 
        "auth/access_restricted.html",
        {
            "admin_contact_email": settings.admin_contact_email,
            "admin_contact_message": settings.admin_contact_message,
            "app_name": settings.app_name
        }
    )


# Login page (public endpoint)
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page - public endpoint."""
    return templates.TemplateResponse(
        request, 
        "auth/login.html",
        {
            "config": settings,
            "admin_contact_email": settings.admin_contact_email
        }
    )


# Logout route (frontend)
@app.get("/logout", response_class=HTMLResponse)
async def logout_page(
    request: Request,
    next: str = "/"
):
    """Frontend logout - clears cookies and redirects."""
    response = RedirectResponse(url=next, status_code=302)
    response.delete_cookie(key="access_token", samesite="lax")
    response.delete_cookie(key="refresh_token", samesite="lax")
    return response


# Register page (redirects to login since registration is disabled)
@app.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    next: str = "/"
):
    """Register page - public registration."""
    return templates.TemplateResponse(
        request,
        "auth/register.html",
        {
            "config": settings,
            "next_url": next
        }
    )


# Root endpoint - requires authentication
@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Root endpoint - redirect to appropriate page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    if current_user:
        # Check if user needs onboarding
        if await user_needs_onboarding(current_user):
            return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
        else:
            return RedirectResponse(url="/expenses/dashboard", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "index.html",
        {"current_user": current_user}
    )


# ============================================================================
# FRONTEND ROUTES FOR EXPENSE MANAGEMENT
# ============================================================================

@app.get("/expenses", response_class=HTMLResponse)
async def expenses_dashboard(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Expenses list page - redirects to household-specific expenses."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Check if user needs onboarding
    if current_user and await user_needs_onboarding(current_user):
        return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
    
    # Get user's households to determine the appropriate redirect
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        
        user_households = await household_service.get_user_households(
            user_id=current_user.id,
            include_inactive=False
        )
        
        if len(user_households) == 0:
            # No households - redirect to onboarding
            return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
        elif len(user_households) == 1:
            # One household - redirect to that household's expenses
            household_id = user_households[0].id
            return RedirectResponse(url=f"/households/{household_id}/expenses", status_code=status.HTTP_302_FOUND)
        else:
            # Multiple households - show household selection
            return templates.TemplateResponse(
                request,
                "expenses/household_selection.html",
                {
                    "current_user": current_user,
                    "households": user_households,
                    "page_title": "Select Household - Expenses"
                }
            )
    except Exception as e:
        logger.error(f"Error getting user households: {e}")
        # Fallback to onboarding if there's an error
        return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
    finally:
        db.close()


@app.get("/expenses/dashboard", response_class=HTMLResponse)
async def expenses_dashboard_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Expenses dashboard page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Check if user needs onboarding
    if current_user and await user_needs_onboarding(current_user):
        return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
    
    # Preload data for performance
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        user_households = await household_service.get_user_households(
            user_id=current_user.id,
            include_inactive=False
        )
        
        # Get recent expenses for the user
        from app.modules.expenses.services.expense_service import ExpenseService
        expense_service = ExpenseService(db)
        
        success, message, recent_expenses = await expense_service.get_user_recent_expenses(
            user_id=current_user.id,
            limit=5
        )
        
        if not success:
            logger.warning(f"Could not load recent expenses: {message}")
            recent_expenses = []
        
        # Format expenses for template
        formatted_expenses = []
        for expense in recent_expenses:
            # Determine payment status based on expense shares
            if hasattr(expense, 'shares') and expense.shares:
                paid_shares = sum(1 for share in expense.shares if share.is_paid)
                total_shares = len(expense.shares)
                if paid_shares == total_shares:
                    payment_status = "paid"
                elif paid_shares == 0:
                    payment_status = "unpaid"
                else:
                    payment_status = "pending"
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
                "created_by": {
                    "username": expense.creator.username if expense.creator else "Unknown",
                    "first_name": expense.creator.first_name if expense.creator else "Unknown",
                    "last_name": expense.creator.last_name if expense.creator else "User"
                },
                "payment_status": payment_status
            }
            formatted_expenses.append(formatted_expense)
        
        return templates.TemplateResponse(
            request,
            "expenses/dashboard.html",
            {
                "current_user": current_user,
                "households": user_households,
                "expenses": formatted_expenses
            }
        )
    except Exception as e:
        logger.error(f"Error loading dashboard data: {e}")
        return templates.TemplateResponse(
            request,
            "expenses/dashboard.html",
            {
                "current_user": current_user,
                "households": [],
                "expenses": []
            }
        )
    finally:
        db.close()


@app.get("/expenses/list", response_class=HTMLResponse)
async def expenses_list(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Expenses list page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "expenses/expenses/list.html",
        {"current_user": current_user}
    )


@app.get("/households", response_class=HTMLResponse)
async def households_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Households management page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Check if user needs onboarding
    if current_user and await user_needs_onboarding(current_user):
        return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
    
    # Preload households data for performance
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        user_households = await household_service.get_user_households(
            user_id=current_user.id,
            include_inactive=False
        )
        
        return templates.TemplateResponse(
            request,
            "expenses/households/list.html",
            {
                "current_user": current_user,
                "households": user_households
            }
        )
    except Exception as e:
        logger.error(f"Error loading households: {e}")
        return templates.TemplateResponse(
            request,
            "expenses/households/list.html",
            {
                "current_user": current_user,
                "households": []
            }
        )
    finally:
        db.close()


@app.get("/households/{household_id}", response_class=HTMLResponse)
async def household_detail(
    request: Request, 
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Household detail page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Fetch household data from database
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        
        # Convert household_id to UUID
        try:
            household_uuid = UUID(household_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid household ID format")
        
        # Get the household details with members
        household = await household_service.get_household_with_members(household_uuid)
        if not household:
            raise HTTPException(status_code=404, detail="Household not found")
        
        # Check if user has permission and get their role
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=household_uuid
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Access denied to this household")
        
        # Get user's membership info to determine role
        user_membership = (
            db.query(UserHousehold)
            .filter(
                UserHousehold.user_id == current_user.id,
                UserHousehold.household_id == household_uuid,
                UserHousehold.is_active == True
            )
            .first()
        )
        
        # Add user role to the household object for template
        household.user_role = user_membership.role.value if user_membership else 'member'
        
        return templates.TemplateResponse(
            request,
            "expenses/households/detail.html",
            {
                "current_user": current_user,
                "household": household,
                "household_id": household_id
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading household details: {e}")
        raise HTTPException(status_code=500, detail="Error loading household details")
    finally:
        db.close()


@app.get("/households/{household_id}/expenses", response_class=HTMLResponse)
async def household_expenses(
    request: Request, 
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Household expenses page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Fetch household data from database
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        
        # Convert household_id to UUID
        try:
            household_uuid = UUID(household_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid household ID format")
        
        # Get the household details with members
        household = await household_service.get_household_with_members(household_uuid)
        if not household:
            raise HTTPException(status_code=404, detail="Household not found")
        
        # Check if user has permission
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=household_uuid
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Access denied to this household")
        
        # Get user's membership info to determine role
        user_membership = (
            db.query(UserHousehold)
            .filter(
                UserHousehold.user_id == current_user.id,
                UserHousehold.household_id == household_uuid,
                UserHousehold.is_active == True
            )
            .first()
        )
        
        # Add user role to the household object for template
        household.user_role = user_membership.role.value if user_membership else 'member'
        
        # Fetch initial expenses data for the template
        from app.modules.expenses.services.expense_service import ExpenseService
        expense_service = ExpenseService(db)
        
        success, message, initial_expenses = await expense_service.get_household_expenses(
            household_id=household_uuid,
            user_id=current_user.id,
            skip=0,
            limit=20,
            sort_by="expense_date",
            sort_order="desc"
        )
        
        if not success:
            logger.warning(f"Could not load initial expenses: {message}")
            initial_expenses = []
        
        # Format expenses for template
        formatted_expenses = []
        for expense in initial_expenses:
            # Determine payment status based on expense shares
            if hasattr(expense, 'shares') and expense.shares:
                paid_shares = sum(1 for share in expense.shares if share.is_paid)
                total_shares = len(expense.shares)
                if paid_shares == total_shares:
                    payment_status_value = "paid"
                elif paid_shares == 0:
                    payment_status_value = "unpaid"
                else:
                    payment_status_value = "pending"
            else:
                payment_status_value = "unpaid"
            
            formatted_expense = {
                "id": str(expense.id),
                "title": expense.title,
                "amount": float(expense.amount),
                "description": expense.description or "",
                "date": expense.expense_date.strftime('%Y-%m-%d'),
                "date_display": expense.expense_date.strftime('%b %d, %Y'),
                "category": expense.category.name if expense.category else "Other",
                "created_by": {
                    "username": expense.creator.username if expense.creator else "Unknown",
                    "first_name": expense.creator.first_name if expense.creator else "Unknown",
                    "last_name": expense.creator.last_name if expense.creator else "User"
                },
                "payment_status": payment_status_value,
                "household_id": str(expense.household_id) if expense.household_id else household_id
            }
            formatted_expenses.append(formatted_expense)
        
        return templates.TemplateResponse(
            request,
            "expenses/expenses/list.html",
            {
                "current_user": current_user,
                "household": household,
                "household_id": household_id,
                "initial_expenses": formatted_expenses
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading household expenses page: {e}")
        raise HTTPException(status_code=500, detail="Error loading household expenses")
    finally:
        db.close()


@app.get("/households/{household_id}/analytics", response_class=HTMLResponse)
async def household_analytics(
    request: Request, 
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Household analytics page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "expenses/analytics/dashboard.html",
        {
            "current_user": current_user,
            "household_id": household_id
        }
    )


@app.get("/analytics", response_class=HTMLResponse)
async def global_analytics(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Global analytics page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "expenses/analytics/dashboard.html",
        {"current_user": current_user}
    )


@app.get("/expenses/create", response_class=HTMLResponse)
async def expense_create_form(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Expense creation form page - redirects to household-specific creation."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Check if user needs onboarding
    if current_user and await user_needs_onboarding(current_user):
        return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
    
    # Get user's households to determine the appropriate redirect
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        
        user_households = await household_service.get_user_households(
            user_id=current_user.id,
            include_inactive=False
        )
        
        if len(user_households) == 0:
            # No households - redirect to onboarding
            return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
        elif len(user_households) == 1:
            # One household - redirect to that household's expense creation
            household_id = user_households[0].id
            return RedirectResponse(url=f"/households/{household_id}/expenses/create", status_code=status.HTTP_302_FOUND)
        else:
            # Multiple households - show household selection for expense creation
            return templates.TemplateResponse(
                request,
                "expenses/household_selection_create.html",
                {
                    "current_user": current_user,
                    "households": user_households,
                    "page_title": "Select Household - Create Expense"
                }
            )
    except Exception as e:
        logger.error(f"Error getting user households: {e}")
        # Fallback to onboarding if there's an error
        return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
    finally:
        db.close()


@app.get("/expenses/create_modal", response_class=HTMLResponse)
async def expense_create_modal(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Expense creation modal content."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "expenses/expenses/create_modal.html",
        {"current_user": current_user}
    )


@app.get("/households/create", response_class=HTMLResponse)
async def household_create_form(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Household creation form page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "expenses/households/create.html",
        {"current_user": current_user}
    )


@app.get("/households/{household_id}/expenses/create", response_class=HTMLResponse)
async def household_expense_create_form(
    request: Request,
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Household-specific expense creation form page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "expenses/expenses/create.html",
        {
            "current_user": current_user,
            "household_id": household_id
        }
    )


# ============================================================================
# HTMX PARTIAL ENDPOINTS (HTML fragments for dynamic loading)
# ============================================================================

@app.get("/partials/households/list", response_class=HTMLResponse)
async def households_list_partial(
    request: Request,
    search: str = "",
    status: str = "",
    role: str = "",
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Households list partial for HTMX loading."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    # Get user's households from API
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        user_households = await household_service.get_user_households(
            user_id=current_user.id,
            include_inactive=(status == "inactive")
        )
        
        # Apply filters
        filtered_households = user_households
        if search:
            filtered_households = [h for h in filtered_households if search.lower() in h.name.lower()]
        if role:
            filtered_households = [h for h in filtered_households if h.user_role == role]
        
        return templates.TemplateResponse(
            request,
            "partials/households/list.html",
            {
                "current_user": current_user,
                "households": filtered_households
            }
        )
    except Exception as e:
        logger.error(f"Error loading households: {e}")
        return HTMLResponse("<div class='text-red-500'>Error loading households</div>", status_code=500)
    finally:
        db.close()


@app.get("/partials/households/create", response_class=HTMLResponse)
async def household_create_partial(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Household creation form partial for HTMX modal loading."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    return templates.TemplateResponse(
        request,
        "partials/households/create.html",
        {"current_user": current_user}
    )


@app.get("/partials/households/join", response_class=HTMLResponse)
async def household_join_partial(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Household join form partial for HTMX modal loading."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    return templates.TemplateResponse(
        request,
        "partials/households/join.html",
        {"current_user": current_user}
    )


@app.get("/partials/expenses/recent", response_class=HTMLResponse)
async def expenses_recent_partial(
    request: Request,
    limit: int = 5,
    household_id: str = None,
    search: str = "",
    category: str = "",
    date_range: str = "",
    min_amount: str = "",
    max_amount: str = "",
    payment_status: str = "",
    created_by: str = "",
    sort_by: str = "date_desc",
    page: int = 1,
    per_page: int = 20,
    view_mode: str = "cards",
    view_type: str = "recent",  # "recent" for simple view, "list" for full view
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Unified expenses partial for HTMX loading - handles both recent and list views."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    # Get expenses from database
    db = next(get_db())
    try:
        from app.modules.expenses.services.expense_service import ExpenseService
        expense_service = ExpenseService(db)
        
        # For list view, use more advanced filtering and pagination
        if view_type == "list":
            # Build filters dictionary
            filters = {}
            if search:
                filters['search'] = search
            if category:
                filters['category'] = category
            if date_range:
                filters['date_range'] = date_range
            # Parse min_amount and max_amount safely
            if min_amount and min_amount.strip():
                try:
                    filters['min_amount'] = float(min_amount)
                except ValueError:
                    pass  # Ignore invalid values
            if max_amount and max_amount.strip():
                try:
                    filters['max_amount'] = float(max_amount)
                except ValueError:
                    pass  # Ignore invalid values
            if payment_status:
                filters['payment_status'] = payment_status
            if created_by:
                filters['created_by'] = created_by
            
            # Convert sort_by to service format
            sort_field = "expense_date"
            sort_order = "desc"
            if sort_by == "date_asc":
                sort_field, sort_order = "expense_date", "asc"
            elif sort_by == "amount_desc":
                sort_field, sort_order = "amount", "desc"
            elif sort_by == "amount_asc":
                sort_field, sort_order = "amount", "asc"
            elif sort_by == "title_asc":
                sort_field, sort_order = "title", "asc"
            elif sort_by == "title_desc":
                sort_field, sort_order = "title", "desc"
            
            # Calculate skip for pagination
            skip = (page - 1) * per_page
            actual_limit = per_page
        else:
            # For recent view, use simpler parameters
            filters = {}
            sort_field = "expense_date"
            sort_order = "desc"
            skip = 0
            actual_limit = limit
        
        if household_id:
            # Get expenses for specific household
            try:
                household_uuid = UUID(household_id)
            except ValueError:
                return HTMLResponse("<div class='text-red-500'>Invalid household ID</div>", status_code=400)
            
            success, message, expenses = await expense_service.get_household_expenses(
                household_id=household_uuid,
                user_id=current_user.id,
                skip=skip,
                limit=actual_limit,
                filters=filters,
                sort_by=sort_field,
                sort_order=sort_order
            )
        else:
            # Get recent expenses across all user's households
            success, message, expenses = await expense_service.get_user_recent_expenses(
                user_id=current_user.id,
                limit=actual_limit
            )
        
        if not success:
            logger.error(f"Error fetching expenses: {message}")
            return HTMLResponse("<div class='text-red-500'>Error loading expenses</div>", status_code=500)
        
        # Format expenses for template
        formatted_expenses = []
        for expense in expenses:
            # Determine payment status based on expense shares
            if hasattr(expense, 'shares') and expense.shares:
                paid_shares = sum(1 for share in expense.shares if share.is_paid)
                total_shares = len(expense.shares)
                if paid_shares == total_shares:
                    payment_status_value = "paid"
                elif paid_shares == 0:
                    payment_status_value = "unpaid"
                else:
                    payment_status_value = "pending"
            else:
                payment_status_value = "unpaid"
            
            formatted_expense = {
                "id": str(expense.id),
                "title": expense.title,
                "amount": float(expense.amount),
                "description": expense.description or "",
                "date": expense.expense_date.strftime('%Y-%m-%d'),
                "date_display": expense.expense_date.strftime('%b %d, %Y'),
                "category": expense.category.name if expense.category else "Other",
                "created_by": {
                    "username": expense.creator.username if expense.creator else "Unknown",
                    "first_name": expense.creator.first_name if expense.creator else "Unknown",
                    "last_name": expense.creator.last_name if expense.creator else "User"
                },
                "payment_status": payment_status_value,
                "household_id": str(expense.household_id) if expense.household_id else household_id
            }
            formatted_expenses.append(formatted_expense)
        
        # Calculate pagination info for list view
        pagination = None
        if view_type == "list":
            total_expenses = len(formatted_expenses)  # Simplified, ideally we'd get actual count
            total_pages = (total_expenses + per_page - 1) // per_page
            pagination = {
                "page": page,
                "per_page": per_page,
                "total": total_expenses,
                "total_pages": total_pages,
                "has_previous": page > 1,
                "has_next": page < total_pages
            }
        
        # Choose template based on view type
        template_name = "partials/expenses/recent.html" if view_type == "recent" else "partials/expenses/list.html"
        
        return templates.TemplateResponse(
            request,
            template_name,
            {
                "current_user": current_user,
                "expenses": formatted_expenses,
                "household_id": household_id,
                "view_mode": view_mode,
                "view_type": view_type,
                "pagination": pagination
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading expenses: {e}")
        return HTMLResponse("<div class='text-red-500'>Error loading expenses</div>", status_code=500)
    finally:
        db.close()


@app.get("/partials/expenses/create", response_class=HTMLResponse)
async def expense_create_partial(
    request: Request,
    household_id: str = None,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Expense creation form partial for HTMX modal loading."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    return templates.TemplateResponse(
        request,
        "partials/expenses/create.html",
        {
            "current_user": current_user,
            "household_id": household_id
        }
    )


@app.get("/partials/expenses/{expense_id}/details", response_class=HTMLResponse)
async def expense_details_partial(
    request: Request,
    expense_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Expense details modal partial for HTMX loading."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    # Get expense details from database
    db = next(get_db())
    try:
        from app.modules.expenses.services.expense_service import ExpenseService
        expense_service = ExpenseService(db)
        
        # Convert expense_id to UUID
        try:
            expense_uuid = UUID(expense_id)
        except ValueError:
            return HTMLResponse("<div class='text-red-500'>Invalid expense ID format</div>", status_code=400)
        
        # Get the expense details
        success, message, expense = await expense_service.get_expense_details(
            expense_id=expense_uuid,
            user_id=current_user.id
        )
        
        if not success:
            logger.error(f"Error fetching expense details: {message}")
            return HTMLResponse("<div class='text-red-500'>Expense not found or access denied</div>", status_code=404)
        
        # Format expense data for template
        if hasattr(expense, 'shares') and expense.shares:
            paid_shares = sum(1 for share in expense.shares if share.is_paid)
            total_shares = len(expense.shares)
            if paid_shares == total_shares:
                payment_status = "paid"
            elif paid_shares == 0:
                payment_status = "unpaid"
            else:
                payment_status = "pending"
        else:
            payment_status = "unpaid"
        
        formatted_expense = {
            "id": str(expense.id),
            "title": expense.title,
            "amount": float(expense.amount),
            "description": expense.description or "",
            "date": expense.expense_date.strftime('%Y-%m-%d'),
            "date_display": expense.expense_date.strftime('%b %d, %Y'),
            "created_at": expense.created_at.strftime('%B %d, %Y at %I:%M %p') if expense.created_at else "Unknown",
            "category": {
                "name": expense.category.name if expense.category else "Other",
                "id": str(expense.category.id) if expense.category else None
            },
            "creator": {
                "username": expense.creator.username if expense.creator else "Unknown",
                "first_name": expense.creator.first_name if expense.creator else "Unknown",
                "last_name": expense.creator.last_name if expense.creator else "User",
                "full_name": f"{expense.creator.first_name} {expense.creator.last_name}" if expense.creator else "Unknown User"
            },
            "payment_status": payment_status,
            "household": {
                "id": str(expense.household_id) if expense.household_id else None,
                "name": expense.household.name if hasattr(expense, 'household') and expense.household else "Unknown Household"
            },
            "shares": []
        }
        
        # Format shares if available
        if hasattr(expense, 'shares') and expense.shares:
            for share in expense.shares:
                formatted_share = {
                    "id": str(share.id),
                    "user": {
                        "id": str(share.user_household.user_id) if share.user_household else "Unknown",
                        "full_name": f"{share.user_household.user.first_name} {share.user_household.user.last_name}" if share.user_household and share.user_household.user else "Unknown User",
                        "username": share.user_household.user.username if share.user_household and share.user_household.user else "unknown"
                    },
                    "amount": float(share.share_amount),
                    "is_paid": share.is_paid,
                    "paid_at": share.paid_at.strftime('%B %d, %Y at %I:%M %p') if share.paid_at else None
                }
                formatted_expense["shares"].append(formatted_share)
        
        return templates.TemplateResponse(
            request,
            "partials/expenses/details.html",
            {
                "current_user": current_user,
                "expense": formatted_expense
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading expense details: {e}")
        return HTMLResponse("<div class='text-red-500'>Error loading expense details</div>", status_code=500)
    finally:
        db.close()


# ============================================================================
# PLACEHOLDER ROUTES FOR FUTURE FEATURES
# ============================================================================

@app.get("/budgets", response_class=HTMLResponse)
async def budgets_list(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Budgets list page (placeholder)."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "placeholder.html",
        {
            "current_user": current_user,
            "page_title": "Budgets",
            "page_description": "Budget management feature coming soon!",
            "feature_name": "Budgets"
        }
    )


@app.get("/budgets/create", response_class=HTMLResponse)
async def budget_create(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Budget creation page (placeholder)."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "placeholder.html",
        {
            "current_user": current_user,
            "page_title": "Create Budget",
            "page_description": "Budget creation feature coming soon!",
            "feature_name": "Budget Creation"
        }
    )


@app.get("/reports", response_class=HTMLResponse)
async def reports_list(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Reports page (placeholder)."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "placeholder.html",
        {
            "current_user": current_user,
            "page_title": "Reports",
            "page_description": "Advanced reporting features coming soon!",
            "feature_name": "Reports"
        }
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Settings page (placeholder)."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "placeholder.html",
        {
            "current_user": current_user,
            "page_title": "Settings",
            "page_description": "User settings and preferences coming soon!",
            "feature_name": "Settings"
        }
    )


async def user_needs_onboarding(current_user) -> bool:
    """Check if user needs to go through onboarding process."""
    if not current_user:
        return False
    
    # Get database session
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        households = await household_service.get_user_households(current_user.id)
        return len(households) == 0
    finally:
        db.close()


# Onboarding Routes
@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_welcome(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Onboarding welcome page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # If user already has households, redirect to dashboard
    if current_user and not await user_needs_onboarding(current_user):
        return RedirectResponse(url="/expenses/dashboard", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "onboarding/welcome.html",
        {"current_user": current_user}
    )


@app.get("/onboarding/create-household", response_class=HTMLResponse)
async def onboarding_create_household(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Onboarding create household page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "onboarding/create_household.html",
        {"current_user": current_user}
    )


@app.get("/onboarding/add-members", response_class=HTMLResponse)
async def onboarding_add_members(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Onboarding add members page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "onboarding/add_members.html",
        {"current_user": current_user}
    )


@app.get("/onboarding/join-household", response_class=HTMLResponse)
async def onboarding_join_household(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Onboarding join household page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "onboarding/join_household.html",
        {"current_user": current_user}
    )


@app.get("/onboarding/complete", response_class=HTMLResponse)
async def onboarding_complete(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Onboarding completion page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "onboarding/complete.html",
        {"current_user": current_user}
    )


@app.get("/payments/history", response_class=HTMLResponse)
async def payment_history_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Payment history page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Check if user needs onboarding
    if current_user and await user_needs_onboarding(current_user):
        return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
    
    # Get payment summary for the user
    db = next(get_db())
    try:
        from app.modules.expenses.services.payment_service import PaymentService
        payment_service = PaymentService(db)
        
        # Get payment summary
        total_paid = 0.0
        total_received = 0.0
        
        # Get recent payments for summary calculation
        payments = payment_service.get_payments_by_filters(
            user_id=current_user.id,
            limit=1000  # Get a large number for summary calculation
        )
        
        for payment in payments:
            if payment.payer_id == current_user.id:
                total_paid += float(payment.amount)
            if payment.payee_id == current_user.id:
                total_received += float(payment.amount)
        
        summary = {
            "total_paid": total_paid,
            "total_received": total_received,
        }
        
        return templates.TemplateResponse(
            request,
            "expenses/payments/history.html",
            {
                "current_user": current_user,
                "summary": summary
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading payment history: {e}")
        # Return with empty summary on error
        summary = {"total_paid": 0.0, "total_received": 0.0}
        return templates.TemplateResponse(
            request,
            "expenses/payments/history.html",
            {
                "current_user": current_user,
                "summary": summary
            }
        )
    finally:
        db.close()


@app.get("/partials/payments/history", response_class=HTMLResponse)
async def payments_history_partial(
    request: Request,
    limit: int = 20,
    household_id: str = None,
    search: str = "",
    payment_type: str = "",
    date_range: str = "",
    min_amount: str = "",
    max_amount: str = "",
    payment_status: str = "",
    payer_payee: str = "",
    sort_by: str = "date_desc",
    page: int = 1,
    per_page: int = 20,
    view_mode: str = "cards",
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Payments history partial for HTMX loading."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    # Get payments from database
    db = next(get_db())
    try:
        from app.modules.expenses.services.payment_service import PaymentService
        payment_service = PaymentService(db)
        
        # Build filters dictionary
        filters = {}
        if search:
            filters['search'] = search
        if payment_type:
            filters['payment_type'] = payment_type
        if date_range:
            filters['date_range'] = date_range
        # Parse min_amount and max_amount safely
        if min_amount and min_amount.strip():
            try:
                filters['min_amount'] = float(min_amount)
            except ValueError:
                pass  # Ignore invalid values
        if max_amount and max_amount.strip():
            try:
                filters['max_amount'] = float(max_amount)
            except ValueError:
                pass  # Ignore invalid values
        if payment_status:
            filters['status'] = payment_status
        if payer_payee:
            filters['payer_payee'] = payer_payee
        
        # Convert sort_by to service format
        sort_field = "payment_date"
        sort_order = "desc"
        if sort_by == "date_asc":
            sort_field, sort_order = "payment_date", "asc"
        elif sort_by == "amount_desc":
            sort_field, sort_order = "amount", "desc"
        elif sort_by == "amount_asc":
            sort_field, sort_order = "amount", "asc"
        
        # Calculate skip for pagination
        skip = (page - 1) * per_page
        
        # Get payments with filters
        payments = payment_service.get_payments_by_filters(
            user_id=current_user.id,
            household_id=UUID(household_id) if household_id else None,
            filters=filters,
            sort_by=sort_field,
            sort_order=sort_order,
            skip=skip,
            limit=per_page
        )
        
        # Format payments for template
        formatted_payments = []
        for payment in payments:
            formatted_payment = {
                "id": str(payment.id),
                "amount": float(payment.amount),
                "description": payment.description or "",
                "payment_date": payment.payment_date,
                "payment_type": payment.payment_type.value if payment.payment_type else "reimbursement",
                "payment_method": payment.payment_method.value if payment.payment_method else None,
                "status": "completed",  # All active payments are considered completed
                "payer_name": payment.payer_name,
                "payee_name": payment.payee_name,
                "linked_expenses": []  # Will be populated if needed
            }
            formatted_payments.append(formatted_payment)
        
        # Create pagination object with iter_pages method
        class PaginationHelper:
            def __init__(self, page, per_page, total, has_prev, has_next, prev_num, next_num):
                self.page = page
                self.per_page = per_page
                self.total = total
                self.has_prev = has_prev
                self.has_next = has_next
                self.prev_num = prev_num
                self.next_num = next_num
            
            def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
                """Generate page numbers for pagination."""
                last = self.page + (self.total - 1) // self.per_page
                for num in range(1, min(last + 1, 10)):  # Limit to 10 pages for simplicity
                    yield num
        
        pagination = PaginationHelper(
            page=page,
            per_page=per_page,
            total=len(formatted_payments),
            has_prev=page > 1,
            has_next=len(formatted_payments) == per_page,
            prev_num=page - 1 if page > 1 else None,
            next_num=page + 1 if len(formatted_payments) == per_page else None
        )
        
        return templates.TemplateResponse(
            request,
            "partials/payments/history.html",
            {
                "payments": formatted_payments,
                "view_mode": view_mode,
                "pagination": pagination,
                "household": {"id": household_id} if household_id else None
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching payments: {e}")
        return HTMLResponse("<div class='text-red-500'>Error loading payments</div>", status_code=500)
    finally:
        db.close()


@app.get("/payments/create", response_class=HTMLResponse)
async def payment_create_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Payment creation page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Check if user needs onboarding
    if current_user and await user_needs_onboarding(current_user):
        return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "expenses/payments/create.html",
        {
            "current_user": current_user,
            "household": None  # No specific household
        }
    )


@app.get("/households/{household_id}/payments/create", response_class=HTMLResponse)
async def household_payment_create_page(
    request: Request,
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Household-specific payment creation page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Check if user needs onboarding
    if current_user and await user_needs_onboarding(current_user):
        return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
    
    # Get household details
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        
        # Convert household_id to UUID
        try:
            household_uuid = UUID(household_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid household ID format")
        
        # Get the household details with members
        household = await household_service.get_household_with_members(household_uuid)
        if not household:
            raise HTTPException(status_code=404, detail="Household not found")
        
        # Check if user has permission
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=household_uuid
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Access denied to this household")
        
        return templates.TemplateResponse(
            request,
            "expenses/payments/create.html",
            {
                "current_user": current_user,
                "household": household,
                "household_id": household_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading household payment creation page: {e}")
        raise HTTPException(status_code=500, detail="Error loading payment creation page")
    finally:
        db.close()


@app.get("/partials/expenses/unpaid", response_class=HTMLResponse)
async def unpaid_expenses_partial(
    request: Request,
    household_id: str = None,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Partial for loading unpaid expenses for the direct payment workflow."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    # Get unpaid expenses from database
    db = next(get_db())
    try:
        from app.modules.expenses.services.expense_service import ExpenseService
        expense_service = ExpenseService(db)
        
        logger.info(f"Loading unpaid expenses for user {current_user.id}, household_id: {household_id}")
        
        # Get unpaid expenses for the user
        if household_id:
            try:
                household_uuid = UUID(household_id)
            except ValueError:
                logger.error(f"Invalid household ID format: {household_id}")
                return HTMLResponse("<div class='text-red-500'>Invalid household ID</div>", status_code=400)
            
            logger.info(f"Getting unpaid expenses for household {household_uuid}")
            # Get unpaid expenses in this household where current user has unpaid shares
            success, message, expenses = await expense_service.get_user_unpaid_expenses(
                user_id=current_user.id,
                household_id=household_uuid
            )
        else:
            logger.info("Getting unpaid expenses across all households")
            # Get unpaid expenses across all households
            success, message, expenses = await expense_service.get_user_unpaid_expenses(
                user_id=current_user.id
            )
        
        logger.info(f"Service call result: success={success}, message={message}, expenses_count={len(expenses) if expenses else 0}")
        
        if not success:
            logger.error(f"Error fetching unpaid expenses: {message}")
            return HTMLResponse("<div class='text-red-500'>Error loading expenses</div>", status_code=500)
        
        # Format expenses for template
        formatted_expenses = []
        for i, expense in enumerate(expenses):
            try:
                logger.info(f"Processing expense {i}: {expense.id} - {expense.title}")
                
                # Calculate user's share for this expense
                user_share = 0.0
                if hasattr(expense, 'shares') and expense.shares:
                    logger.info(f"Expense has {len(expense.shares)} shares")
                    user_shares = [share for share in expense.shares if share.user_household.user_id == current_user.id and not share.is_paid]
                    logger.info(f"User has {len(user_shares)} unpaid shares")
                    user_share = sum(float(share.share_amount) for share in user_shares)
                else:
                    logger.info("Expense has no shares")
                
                if user_share > 0:  # Only include if user has unpaid shares
                    formatted_expense = {
                        "id": str(expense.id),
                        "title": expense.title,
                        "amount": float(expense.amount),
                        "user_share": user_share,
                        "description": expense.description or "",
                        "date": expense.expense_date.strftime('%Y-%m-%d'),
                        "date_display": expense.expense_date.strftime('%b %d, %Y'),
                        "category": {
                            "name": expense.category.name if expense.category else "Other",
                            "id": str(expense.category.id) if expense.category else None
                        },
                        "creator": {
                            "username": expense.creator.username if expense.creator else "Unknown",
                            "first_name": expense.creator.first_name if expense.creator else "Unknown",
                            "last_name": expense.creator.last_name if expense.creator else "User",
                            "full_name": f"{expense.creator.first_name} {expense.creator.last_name}" if expense.creator else "Unknown User"
                        }
                    }
                    formatted_expenses.append(formatted_expense)
                    logger.info(f"Added expense {expense.id} with user_share {user_share}")
                else:
                    logger.info(f"Skipped expense {expense.id} - no unpaid user shares")
                    
            except Exception as e:
                logger.error(f"Error processing expense {expense.id if hasattr(expense, 'id') else 'unknown'}: {e}")
                continue
        
        logger.info(f"Formatted {len(formatted_expenses)} expenses for template")
        
        return templates.TemplateResponse(
            request,
            "partials/expenses/unpaid.html",
            {
                "unpaid_expenses": formatted_expenses,
                "household": {"id": household_id} if household_id else None
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading unpaid expenses: {e}", exc_info=True)
        return HTMLResponse("<div class='text-red-500'>Error loading expenses</div>", status_code=500)
    finally:
        db.close()


@app.get("/partials/expenses/user-summary", response_class=HTMLResponse)
async def user_expenses_summary_partial(
    request: Request,
    payee_id: str,
    household_id: str = None,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Partial for loading user expenses summary for bulk payment workflow."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    if not payee_id:
        return HTMLResponse("<div class='text-gray-500'>Select a person to see their expenses</div>")
    
    # Get user expenses from database
    db = next(get_db())
    try:
        from app.modules.expenses.services.expense_service import ExpenseService
        from app.modules.auth.models.user import User
        
        expense_service = ExpenseService(db)
        
        # Get the payee user
        try:
            payee_uuid = UUID(payee_id)
        except ValueError:
            return HTMLResponse("<div class='text-red-500'>Invalid user ID</div>", status_code=400)
        
        payee_user = db.query(User).filter(User.id == payee_uuid).first()
        if not payee_user:
            return HTMLResponse("<div class='text-red-500'>User not found</div>", status_code=404)
        
        # Get unpaid expenses where the current user owes the payee
        if household_id:
            try:
                household_uuid = UUID(household_id)
            except ValueError:
                return HTMLResponse("<div class='text-red-500'>Invalid household ID</div>", status_code=400)
            
            success, message, expenses = await expense_service.get_user_unpaid_expenses_for_payee(
                payer_id=current_user.id,
                payee_id=payee_uuid,
                household_id=household_uuid
            )
        else:
            success, message, expenses = await expense_service.get_user_unpaid_expenses_for_payee(
                payer_id=current_user.id,
                payee_id=payee_uuid
            )
        
        if not success:
            logger.error(f"Error fetching user expenses: {message}")
            return HTMLResponse("<div class='text-red-500'>Error loading expenses</div>", status_code=500)
        
        # Format expenses and calculate total
        formatted_expenses = []
        total_amount = 0.0
        
        for expense in expenses:
            # Calculate user's share for this expense
            user_share = 0.0
            if hasattr(expense, 'shares') and expense.shares:
                user_shares = [share for share in expense.shares if share.user_household.user_id == current_user.id and not share.is_paid]
                user_share = sum(float(share.share_amount) for share in user_shares)
            
            if user_share > 0:  # Only include if user has unpaid shares
                formatted_expense = {
                    "id": str(expense.id),
                    "title": expense.title,
                    "amount": float(expense.amount),
                    "user_share": user_share,
                    "description": expense.description or "",
                    "date": expense.expense_date.strftime('%Y-%m-%d'),
                    "date_display": expense.expense_date.strftime('%b %d, %Y'),
                    "category": {
                        "name": expense.category.name if expense.category else "Other",
                        "id": str(expense.category.id) if expense.category else None
                    }
                }
                formatted_expenses.append(formatted_expense)
                total_amount += user_share
        
        return templates.TemplateResponse(
            request,
            "partials/expenses/user-summary.html",
            {
                "user_expenses": formatted_expenses,
                "user_name": f"{payee_user.first_name} {payee_user.last_name}",
                "total_amount": total_amount
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading user expenses summary: {e}")
        return HTMLResponse("<div class='text-red-500'>Error loading expenses summary</div>", status_code=500)
    finally:
        db.close()


@app.get("/partials/expenses/linkable", response_class=HTMLResponse)
async def linkable_expenses_partial(
    request: Request,
    household_id: str = None,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Partial for loading linkable expenses for general payment workflow."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    # Get linkable expenses from database
    db = next(get_db())
    try:
        from app.modules.expenses.services.expense_service import ExpenseService
        expense_service = ExpenseService(db)
        
        # Get unpaid expenses that can be linked to a payment
        if household_id:
            try:
                household_uuid = UUID(household_id)
            except ValueError:
                return HTMLResponse("<div class='text-red-500'>Invalid household ID</div>", status_code=400)
            
            success, message, expenses = await expense_service.get_user_unpaid_expenses(
                user_id=current_user.id,
                household_id=household_uuid
            )
        else:
            success, message, expenses = await expense_service.get_user_unpaid_expenses(
                user_id=current_user.id
            )
        
        if not success:
            logger.error(f"Error fetching linkable expenses: {message}")
            return HTMLResponse("<div class='text-red-500'>Error loading expenses</div>", status_code=500)
        
        # Format expenses for template
        formatted_expenses = []
        for expense in expenses:
            # Calculate user's share for this expense
            user_share = 0.0
            if hasattr(expense, 'shares') and expense.shares:
                user_shares = [share for share in expense.shares if share.user_household.user_id == current_user.id and not share.is_paid]
                user_share = sum(float(share.share_amount) for share in user_shares)
            
            if user_share > 0:  # Only include if user has unpaid shares
                formatted_expense = {
                    "id": str(expense.id),
                    "title": expense.title,
                    "amount": float(expense.amount),
                    "user_share": user_share,
                    "description": expense.description or "",
                    "date": expense.expense_date.strftime('%Y-%m-%d'),
                    "date_display": expense.expense_date.strftime('%b %d, %Y'),
                    "category": {
                        "name": expense.category.name if expense.category else "Other",
                        "id": str(expense.category.id) if expense.category else None
                    },
                    "creator": {
                        "username": expense.creator.username if expense.creator else "Unknown",
                        "first_name": expense.creator.first_name if expense.creator else "Unknown",
                        "last_name": expense.creator.last_name if expense.creator else "User",
                        "full_name": f"{expense.creator.first_name} {expense.creator.last_name}" if expense.creator else "Unknown User"
                    }
                }
                formatted_expenses.append(formatted_expense)
        
        return templates.TemplateResponse(
            request,
            "partials/expenses/linkable.html",
            {
                "linkable_expenses": formatted_expenses
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading linkable expenses: {e}")
        return HTMLResponse("<div class='text-red-500'>Error loading expenses</div>", status_code=500)
    finally:
        db.close()


@app.get("/expenses/{expense_id}", response_class=HTMLResponse)
async def expense_detail_page(
    request: Request,
    expense_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Full page expense detail view."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Get expense details from database - reuse the same logic as the partial
    db = next(get_db())
    try:
        from app.modules.expenses.services.expense_service import ExpenseService
        expense_service = ExpenseService(db)
        
        # Convert expense_id to UUID
        try:
            expense_uuid = UUID(expense_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expense ID format")
        
        # Get the expense details
        success, message, expense = await expense_service.get_expense_details(
            expense_id=expense_uuid,
            user_id=current_user.id
        )
        
        if not success:
            logger.error(f"Error fetching expense details: {message}")
            raise HTTPException(status_code=404, detail="Expense not found or access denied")
        
        # Format expense data for template (same as partial)
        if hasattr(expense, 'shares') and expense.shares:
            paid_shares = sum(1 for share in expense.shares if share.is_paid)
            total_shares = len(expense.shares)
            if paid_shares == total_shares:
                payment_status = "paid"
            elif paid_shares == 0:
                payment_status = "unpaid"
            else:
                payment_status = "pending"
        else:
            payment_status = "unpaid"
        
        formatted_expense = {
            "id": str(expense.id),
            "title": expense.title,
            "amount": float(expense.amount),
            "description": expense.description or "",
            "date": expense.expense_date.strftime('%Y-%m-%d'),
            "date_display": expense.expense_date.strftime('%b %d, %Y'),
            "created_at": expense.created_at.strftime('%B %d, %Y at %I:%M %p') if expense.created_at else "Unknown",
            "category": {
                "name": expense.category.name if expense.category else "Other",
                "id": str(expense.category.id) if expense.category else None
            },
            "creator": {
                "username": expense.creator.username if expense.creator else "Unknown",
                "first_name": expense.creator.first_name if expense.creator else "Unknown",
                "last_name": expense.creator.last_name if expense.creator else "User",
                "full_name": f"{expense.creator.first_name} {expense.creator.last_name}" if expense.creator else "Unknown User"
            },
            "payment_status": payment_status,
            "household": {
                "id": str(expense.household_id) if expense.household_id else None,
                "name": expense.household.name if hasattr(expense, 'household') and expense.household else "Unknown Household"
            },
            "shares": []
        }
        
        # Format shares if available
        if hasattr(expense, 'shares') and expense.shares:
            for share in expense.shares:
                formatted_share = {
                    "id": str(share.id),
                    "user": {
                        "id": str(share.user_household.user_id) if share.user_household else "Unknown",
                        "full_name": f"{share.user_household.user.first_name} {share.user_household.user.last_name}" if share.user_household and share.user_household.user else "Unknown User",
                        "username": share.user_household.user.username if share.user_household and share.user_household.user else "unknown"
                    },
                    "amount": float(share.share_amount),
                    "is_paid": share.is_paid,
                    "paid_at": share.paid_at.strftime('%B %d, %Y at %I:%M %p') if share.paid_at else None
                }
                formatted_expense["shares"].append(formatted_share)
        
        return templates.TemplateResponse(
            request,
            "expenses/expenses/detail.html",
            {
                "current_user": current_user,
                "expense": formatted_expense
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading expense detail page: {e}")
        raise HTTPException(status_code=500, detail="Error loading expense details")
    finally:
        db.close()


@app.get("/partials/payments/{payment_id}/details", response_class=HTMLResponse)
async def payment_details_partial(
    request: Request,
    payment_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Partial for displaying payment details in a modal."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    db = next(get_db())
    try:
        from app.modules.expenses.services.payment_service import PaymentService
        payment_service = PaymentService(db)
        
        # Convert payment_id to UUID
        try:
            payment_uuid = UUID(payment_id)
        except ValueError:
            return HTMLResponse("<div class='text-red-500'>Invalid payment ID format</div>", status_code=400)
        
        # Get payment details
        success, message, payment = await payment_service.get_payment_details(
            payment_id=payment_uuid,
            current_user_id=current_user.id
        )
        
        if not success:
            if "not found" in message.lower():
                return HTMLResponse("<div class='text-red-500'>Payment not found</div>", status_code=404)
            else:
                return HTMLResponse(f"<div class='text-red-500'>{message}</div>", status_code=403)
        
        # Format payment for template
        formatted_payment = {
            "id": str(payment.id),
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_type": payment.payment_type.value if payment.payment_type else "reimbursement",
            "payment_method": payment.payment_method.value if payment.payment_method else None,
            "description": payment.description,
            "reference_number": payment.reference_number,
            "payment_date": payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else None,
            "payment_date_display": payment.payment_date.strftime('%b %d, %Y') if payment.payment_date else None,
            "created_at": payment.created_at.strftime('%b %d, %Y at %I:%M %p') if payment.created_at else None,
            "payer": None,
            "payee": None,
            "household": None,
            "expense_shares": []
        }
        
        # Add payer/payee info if available
        if hasattr(payment, 'payer') and payment.payer:
            formatted_payment["payer"] = {
                "id": str(payment.payer.id),
                "username": payment.payer.username,
                "full_name": f"{payment.payer.first_name} {payment.payer.last_name}",
                "first_name": payment.payer.first_name,
                "last_name": payment.payer.last_name
            }
        
        if hasattr(payment, 'payee') and payment.payee:
            formatted_payment["payee"] = {
                "id": str(payment.payee.id),
                "username": payment.payee.username,
                "full_name": f"{payment.payee.first_name} {payment.payee.last_name}",
                "first_name": payment.payee.first_name,
                "last_name": payment.payee.last_name
            }
        
        # Add household info if available
        if hasattr(payment, 'household') and payment.household:
            formatted_payment["household"] = {
                "id": str(payment.household.id),
                "name": payment.household.name
            }
        
        return templates.TemplateResponse(
            request,
            "partials/payments/details.html",
            {
                "payment": formatted_payment,
                "current_user": current_user
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching payment details: {e}")
        return HTMLResponse("<div class='text-red-500'>Error loading payment details</div>", status_code=500)
    finally:
        db.close()


@app.get("/partials/payments/{payment_id}/edit", response_class=HTMLResponse)
async def payment_edit_partial(
    request: Request,
    payment_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Partial for editing payment details in a modal."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    db = next(get_db())
    try:
        from app.modules.expenses.services.payment_service import PaymentService
        payment_service = PaymentService(db)
        
        # Convert payment_id to UUID
        try:
            payment_uuid = UUID(payment_id)
        except ValueError:
            return HTMLResponse("<div class='text-red-500'>Invalid payment ID format</div>", status_code=400)
        
        # Get payment details
        success, message, payment = await payment_service.get_payment_details(
            payment_id=payment_uuid,
            current_user_id=current_user.id
        )
        
        if not success:
            if "not found" in message.lower():
                return HTMLResponse("<div class='text-red-500'>Payment not found</div>", status_code=404)
            else:
                return HTMLResponse(f"<div class='text-red-500'>{message}</div>", status_code=403)
        
        # Format payment for template
        formatted_payment = {
            "id": str(payment.id),
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_type": payment.payment_type.value if payment.payment_type else "reimbursement",
            "payment_method": payment.payment_method.value if payment.payment_method else "",
            "description": payment.description or "",
            "reference_number": payment.reference_number or "",
            "payment_date": payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else None,
        }
        
        return templates.TemplateResponse(
            request,
            "partials/payments/edit.html",
            {
                "payment": formatted_payment,
                "current_user": current_user
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching payment for edit: {e}")
        return HTMLResponse("<div class='text-red-500'>Error loading payment for editing</div>", status_code=500)
    finally:
        db.close()


# ============================================================================
# HOUSEHOLD MEMBER MANAGEMENT ROUTES (for HTMX forms)
# ============================================================================

@app.post("/households/{household_id}/invite-member")
async def invite_member_frontend(
    household_id: str,
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Frontend route for inviting members via HTMX forms."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    # Delegate to the API endpoint
    from app.modules.expenses.routers.households import invite_member
    from fastapi import Form
    
    # Get form data from request
    form = await request.form()
    email = form.get("email")
    role = form.get("role", "member")
    nickname = form.get("nickname")
    
    try:
        household_uuid = UUID(household_id)
        return await invite_member(
            household_id=household_uuid,
            email=email,
            role=role,
            nickname=nickname,
            current_user=current_user
        )
    except ValueError:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content="""
            <div class="p-4 bg-red-50 border border-red-200 rounded-md">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">Invalid Household ID</h3>
                        <div class="mt-2 text-sm text-red-700">
                            <p>The household ID format is invalid.</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
            status_code=400
        )


@app.put("/households/{household_id}/members/{user_id}")
async def update_member_frontend(
    household_id: str,
    user_id: str,
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Frontend route for updating members via HTMX forms."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    # Delegate to the API endpoint
    from app.modules.expenses.routers.households import update_member
    
    # Get form data from request
    form = await request.form()
    nickname = form.get("nickname")
    role = form.get("role", "member")
    
    try:
        household_uuid = UUID(household_id)
        user_uuid = UUID(user_id)
        return await update_member(
            household_id=household_uuid,
            user_id=user_uuid,
            nickname=nickname,
            role=role,
            current_user=current_user
        )
    except ValueError:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content="""
            <div class="p-4 bg-red-50 border border-red-200 rounded-md">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">Invalid ID Format</h3>
                        <div class="mt-2 text-sm text-red-700">
                            <p>The household or user ID format is invalid.</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
            status_code=400
        )


@app.delete("/households/{household_id}/members/{user_id}")
async def remove_member_frontend(
    household_id: str,
    user_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Frontend route for removing members via HTMX forms."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    # Delegate to the API endpoint
    from app.modules.expenses.routers.households import remove_member
    
    try:
        household_uuid = UUID(household_id)
        user_uuid = UUID(user_id)
        return await remove_member(
            household_id=household_uuid,
            user_id=user_uuid,
            current_user=current_user
        )
    except ValueError:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content="""
            <div class="p-4 bg-red-50 border border-red-200 rounded-md">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">Invalid ID Format</h3>
                        <div class="mt-2 text-sm text-red-700">
                            <p>The household or user ID format is invalid.</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
            status_code=400
        )


@app.get("/join")
async def join_household_page(
    request: Request,
    code: str = None,
    current_user = Depends(get_current_user_optional)
):
    """Page for joining a household using an invite code from a shared link."""
    if not code:
        return RedirectResponse(url="/", status_code=302)
    
    try:
        # Find household by invite code (publicly accessible)
        db = next(get_db())
        from app.modules.expenses.models.household import Household
        from app.modules.expenses.models.user_household import UserHousehold
        
        household = db.query(Household).filter(Household.invite_code == code).first()
        
        if not household:
            return templates.TemplateResponse(
                request,
                "join_error.html",
                {
                    "error": "Invalid or expired invite code",
                    "code": code
                }
            )
        
        # If user is not authenticated, show join page with login options
        if not current_user:
            return templates.TemplateResponse(
                request,
                "join_household.html",
                {
                    "household": household,
                    "code": code,
                    "current_user": None
                }
            )
        
        # Check if user is already a member
        existing_membership = db.query(UserHousehold).filter(
            UserHousehold.household_id == household.id,
            UserHousehold.user_id == current_user.id,
            UserHousehold.is_active == True
        ).first()
        
        if existing_membership:
            return RedirectResponse(url=f"/households/{household.id}", status_code=302)
        
        # User is authenticated but not a member - show join page
        return templates.TemplateResponse(
            request,
            "join_household.html",
            {
                "household": household,
                "code": code,
                "current_user": current_user
            }
        )
        
    except Exception as e:
        logger.error(f"Error in join page: {e}")
        return templates.TemplateResponse(
            request,
            "join_error.html",
            {
                "error": "An error occurred while processing your request",
                "code": code
            }
        )
    finally:
        db.close()


@app.post("/join")
async def join_household_action(
    request: Request,
    code: str = Form(...),
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Process joining a household using an invite code."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("Authentication required", status_code=401)
    
    try:
        db = next(get_db())
        
        # Find household by invite code
        household = db.query(Household).filter(Household.invite_code == code).first()
        
        if not household:
            return HTMLResponse(
                """
                <div class="p-3 bg-red-50 border border-red-200 rounded-md">
                    <div class="flex">
                        <div class="flex-shrink-0">
                            <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                            </svg>
                        </div>
                        <div class="ml-3">
                            <h3 class="text-sm font-medium text-red-800">Invalid Invite Code</h3>
                            <div class="mt-2 text-sm text-red-700">
                                <p>The invite code is invalid or has expired.</p>
                            </div>
                        </div>
                    </div>
                </div>
                """,
                status_code=400
            )
        
        # Check if user is already a member
        existing_membership = db.query(HouseholdMember).filter(
            HouseholdMember.household_id == household.id,
            HouseholdMember.user_id == current_user.id
        ).first()
        
        if existing_membership:
            return HTMLResponse(
                f"""
                <div class="p-3 bg-blue-50 border border-blue-200 rounded-md">
                    <div class="flex">
                        <div class="flex-shrink-0">
                            <svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
                            </svg>
                        </div>
                        <div class="ml-3">
                            <h3 class="text-sm font-medium text-blue-800">Already a Member</h3>
                            <div class="mt-2 text-sm text-blue-700">
                                <p>You're already a member of {household.name}!</p>
                                <a href="/households/{household.id}" class="font-medium underline">Go to household</a>
                            </div>
                        </div>
                    </div>
                </div>
                <script>
                    // Clean up localStorage since user is already a member
                    localStorage.removeItem('household_invite_code');
                    localStorage.removeItem('household_invite_timestamp');
                    console.log('Cleaned up invite code from localStorage - user already a member');
                    
                    setTimeout(() => window.location.href = '/households/{household.id}', 2000);
                </script>
                """
            )
        
        # Add user as a member
        new_member = HouseholdMember(
            household_id=household.id,
            user_id=current_user.id,
            role="member",
            nickname=None
        )
        db.add(new_member)
        db.commit()
        
        return HTMLResponse(
            f"""
            <div class="p-3 bg-green-50 border border-green-200 rounded-md">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-green-800">Welcome to {household.name}!</h3>
                        <div class="mt-2 text-sm text-green-700">
                            <p>You've successfully joined the household.</p>
                            <a href="/households/{household.id}" class="font-medium underline">Go to household</a>
                        </div>
                    </div>
                </div>
            </div>
            <script>
                // Clean up localStorage after successful join
                localStorage.removeItem('household_invite_code');
                localStorage.removeItem('household_invite_timestamp');
                console.log('Cleaned up invite code from localStorage after successful join');
                
                setTimeout(() => window.location.href = '/households/{household.id}', 2000);
            </script>
            """
        )
        
    except Exception as e:
        logger.error(f"Error joining household: {e}")
        return HTMLResponse(
            """
            <div class="p-3 bg-red-50 border border-red-200 rounded-md">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">Error</h3>
                        <div class="mt-2 text-sm text-red-700">
                            <p>An error occurred while joining the household. Please try again.</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
            status_code=500
        )
    finally:
        db.close()


# ============================================================================
# API COUNTERPARTS FOR MOBILE APP DEVELOPMENT
# ============================================================================

@app.get("/api/join")
async def join_household_info_api(
    code: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """API endpoint for getting household join information using an invite code."""
    if not code:
        raise HTTPException(status_code=400, detail="Invite code is required")
    
    try:
        db = next(get_db())
        from app.modules.expenses.models.household import Household
        from app.modules.expenses.models.user_household import UserHousehold
        
        # Find household by invite code
        household = db.query(Household).filter(Household.invite_code == code).first()
        
        if not household:
            raise HTTPException(status_code=404, detail="Invalid or expired invite code")
        
        # Check if user is already a member (if authenticated)
        is_member = False
        if current_user:
            existing_membership = db.query(UserHousehold).filter(
                UserHousehold.household_id == household.id,
                UserHousehold.user_id == current_user.id,
                UserHousehold.is_active == True
            ).first()
            is_member = existing_membership is not None
        
        return {
            "success": True,
            "household": {
                "id": str(household.id),
                "name": household.name,
                "description": household.description,
                "invite_code": household.invite_code
            },
            "user_status": {
                "is_authenticated": current_user is not None,
                "is_member": is_member,
                "user_id": str(current_user.id) if current_user else None,
                "email": current_user.email if current_user else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in join API: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your request")
    finally:
        db.close()


@app.post("/api/join")
async def join_household_api(
    code: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """API endpoint for joining a household using an invite code."""
    if settings.require_authentication_for_all and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not code:
        raise HTTPException(status_code=400, detail="Invite code is required")
    
    try:
        db = next(get_db())
        from app.modules.expenses.models.household import Household
        from app.modules.expenses.models.user_household import UserHousehold
        from app.modules.expenses.models.household_member import HouseholdMember
        
        # Find household by invite code
        household = db.query(Household).filter(Household.invite_code == code).first()
        
        if not household:
            raise HTTPException(status_code=404, detail="Invalid or expired invite code")
        
        # Check if user is already a member
        existing_membership = db.query(UserHousehold).filter(
            UserHousehold.household_id == household.id,
            UserHousehold.user_id == current_user.id,
            UserHousehold.is_active == True
        ).first()
        
        if existing_membership:
            return {
                "success": True,
                "message": f"You're already a member of {household.name}",
                "household": {
                    "id": str(household.id),
                    "name": household.name,
                    "description": household.description
                },
                "action": "already_member"
            }
        
        # Add user as a member (using the new UserHousehold model)
        new_membership = UserHousehold(
            user_id=current_user.id,
            household_id=household.id,
            role="member",
            nickname=None,
            is_active=True
        )
        db.add(new_membership)
        db.commit()
        db.refresh(new_membership)
        
        return {
            "success": True,
            "message": f"Successfully joined {household.name}!",
            "household": {
                "id": str(household.id),
                "name": household.name,
                "description": household.description
            },
            "membership": {
                "id": str(new_membership.id),
                "role": new_membership.role.value,
                "joined_at": new_membership.created_at.isoformat() if new_membership.created_at else None
            },
            "action": "joined"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining household via API: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while joining the household")
    finally:
        db.close()


@app.get("/api/households/{household_id}/join-info")
async def household_join_info_api(
    request: Request,
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """API endpoint for getting household join information by household ID."""
    if settings.require_authentication_for_all and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        household_uuid = UUID(household_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid household ID format")
    
    try:
        db = next(get_db())
        from app.modules.expenses.models.household import Household
        from app.modules.expenses.models.user_household import UserHousehold
        
        # Get household
        household = db.query(Household).filter(Household.id == household_uuid).first()
        if not household:
            raise HTTPException(status_code=404, detail="Household not found")
        
        # Check if user has permission to access this household
        has_permission = False
        if current_user:
            membership = db.query(UserHousehold).filter(
                UserHousehold.household_id == household_uuid,
                UserHousehold.user_id == current_user.id,
                UserHousehold.is_active == True
            ).first()
            has_permission = membership is not None and membership.role in ["admin", "member"]
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Access denied to this household")
        
        return {
            "success": True,
            "household": {
                "id": str(household.id),
                "name": household.name,
                "description": household.description,
                "invite_code": household.invite_code,
                "join_link": f"{request.url.scheme}://{request.url.netloc}/join?code={household.invite_code}"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting household join info: {e}")
        raise HTTPException(status_code=500, detail="Error getting household information")
    finally:
        db.close()


# Favicon route
@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.svg", media_type="image/svg+xml")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
