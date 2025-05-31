"""
Main FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from uuid import UUID
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

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
)
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
            "expense_date": expense.expense_date.strftime('%Y-%m-%d'),
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
            "expense_date": expense.expense_date.strftime('%Y-%m-%d'),
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
