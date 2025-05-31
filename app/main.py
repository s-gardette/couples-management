"""
Main FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
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
        
        # Mock recent expenses data for now
        mock_expenses = [
            {
                "id": "1",
                "title": "Grocery Shopping",
                "amount": 89.50,
                "description": "Weekly groceries from Walmart",
                "date": "2024-01-15",
                "category": "Food & Dining",
                "created_by": {"username": "john_doe", "first_name": "John", "last_name": "Doe"},
                "payment_status": "paid"
            },
            {
                "id": "2", 
                "title": "Electric Bill",
                "amount": 145.30,
                "description": "Monthly electricity bill",
                "date": "2024-01-14",
                "category": "Utilities",
                "created_by": {"username": "jane_doe", "first_name": "Jane", "last_name": "Doe"},
                "payment_status": "pending"
            }
        ]
        
        return templates.TemplateResponse(
            request,
            "expenses/dashboard.html",
            {
                "current_user": current_user,
                "households": user_households,
                "expenses": mock_expenses
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
    
    return templates.TemplateResponse(
        request,
        "expenses/households/detail.html",
        {
            "current_user": current_user,
            "household_id": household_id
        }
    )


@app.get("/households/{household_id}/expenses", response_class=HTMLResponse)
async def household_expenses(
    request: Request, 
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Household expenses page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "expenses/expenses/list.html",
        {
            "current_user": current_user,
            "household_id": household_id
        }
    )


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
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Recent expenses partial for HTMX loading."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    # Get recent expenses from API
    import requests
    import json
    
    try:
        # Build API URL
        if household_id:
            api_url = f"http://localhost:8000/api/households/{household_id}/expenses"
        else:
            api_url = "http://localhost:8000/api/expenses/recent"
        
        # Make API request with authentication
        headers = {
            "Authorization": f"Bearer {current_user.access_token if hasattr(current_user, 'access_token') else 'dummy'}"
        }
        params = {"limit": limit}
        
        # For now, let's create mock data since we need to fix the API integration
        mock_expenses = [
            {
                "id": "1",
                "title": "Grocery Shopping",
                "amount": 89.50,
                "description": "Weekly groceries from Walmart",
                "date": "2024-01-15",
                "category": "Food & Dining",
                "created_by": {"username": "john_doe", "first_name": "John", "last_name": "Doe"},
                "payment_status": "paid"
            },
            {
                "id": "2", 
                "title": "Electric Bill",
                "amount": 145.30,
                "description": "Monthly electricity bill",
                "date": "2024-01-14",
                "category": "Utilities",
                "created_by": {"username": "jane_doe", "first_name": "Jane", "last_name": "Doe"},
                "payment_status": "pending"
            }
        ]
        
        return templates.TemplateResponse(
            request,
            "partials/expenses/recent.html",
            {
                "current_user": current_user,
                "expenses": mock_expenses[:limit],
                "household_id": household_id
            }
        )
    except Exception as e:
        logger.error(f"Error loading recent expenses: {e}")
        return HTMLResponse("<div class='text-red-500'>Error loading expenses</div>", status_code=500)


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
