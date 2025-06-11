"""
Main frontend routes for dashboard, profile, and other core pages.
"""

import logging
from typing import List
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse

from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.modules.auth.dependencies import get_current_user_from_cookie_or_header, get_current_user_optional
from app.modules.auth.models.user import User
from app.modules.auth.services.auth_service import AuthService
from app.modules.expenses.services import HouseholdService

router = APIRouter()

# Setup Enhanced Jinja2 templates with automatic global context
from app.core.templates import templates
logger = logging.getLogger(__name__)


# Access restricted page (only public endpoint)
@router.get("/access-restricted", response_class=HTMLResponse)
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
@router.get("/login", response_class=HTMLResponse)
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


# Logout route (frontend and API)
@router.post("/logout")
@router.get("/logout")
async def logout(
    request: Request,
    next: str = Query("/"),
    current_user: User = Depends(get_current_user_from_cookie_or_header),
    db: Session = Depends(get_db)
):
    """Logout - supports both frontend and API requests."""
    # Initialize auth service
    auth_service = AuthService()
    
    # Get the token from request
    token = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        # Try cookie
        token = request.cookies.get("access_token")
    
    # If we have a user and token, properly logout via service
    if current_user and token:
        try:
            await auth_service.logout(db, token)
        except Exception as e:
            # Log error but don't fail the logout
            logger.warning(f"Error during logout cleanup: {e}")
    
    # Create redirect response
    response = RedirectResponse(url=next, status_code=302)
    
    # Clear the cookie
    response.delete_cookie("access_token", path="/")
    
    return response


# Admin logout route (frontend and API)
@router.post("/admin/logout")
@router.get("/admin/logout")
async def admin_logout(
    request: Request,
    next: str = Query("/admin/login"),
    current_user: User = Depends(get_current_user_from_cookie_or_header),
    db: Session = Depends(get_db)
):
    """Admin logout - supports both frontend and API requests."""
    # Initialize auth service
    auth_service = AuthService()
    
    # Get the token from request
    token = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        # Try cookie
        token = request.cookies.get("access_token")
    
    # If we have a user and token, properly logout via service
    if current_user and token:
        try:
            await auth_service.logout(db, token)
        except Exception as e:
            # Log error but don't fail the logout
            logger.warning(f"Error during admin logout cleanup: {e}")
    
    # Create redirect response
    response = RedirectResponse(url=next, status_code=302)
    
    # Clear the cookie
    response.delete_cookie("access_token", path="/")
    
    return response


# Register page (public endpoint)
@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    next: str = "/"
):
    """Register page - public endpoint."""
    return templates.TemplateResponse(
        request, 
        "auth/register.html",
        {
            "config": settings,
            "next": next
        }
    )


# Root/Dashboard page
@router.get("/", response_class=HTMLResponse)
async def home_page(
    request: Request,
    current_user = Depends(get_current_user_optional)
):
    """Home page with marketing or dashboard redirect."""
    # If user is authenticated, redirect to dashboard
    if current_user:
        if await user_needs_onboarding(current_user):
            return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
        else:
            return RedirectResponse(url="/expenses", status_code=status.HTTP_302_FOUND)
    
    # Show marketing page for unauthenticated users
    return templates.TemplateResponse(
        request,
        "home.html",
        {"current_user": current_user}
    )


# Dashboard page
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current_user: User = Depends(get_current_user_from_cookie_or_header),
):
    """Main dashboard page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    # Check if user needs onboarding
    if current_user and await user_needs_onboarding(current_user):
        return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)

    # Preload user's households for navigation
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        user_households = await household_service.get_user_households(
            user_id=current_user.id,
            include_inactive=False
        )
        
        return templates.TemplateResponse(
            request,
            "main/dashboard.html",
            {
                "current_user": current_user,
                "households": user_households
            }
        )
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return templates.TemplateResponse(
            request,
            "main/dashboard.html",
            {
                "current_user": current_user,
                "households": []
            }
        )
    finally:
        db.close()


# Profile page
@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    current_user: User = Depends(get_current_user_from_cookie_or_header),
):
    """User profile page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    # Get user's household memberships for display
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        user_households = await household_service.get_user_households(
            user_id=current_user.id,
            include_inactive=False
        )
        
        return templates.TemplateResponse(
            request,
            "auth/profile.html",
            {
                "current_user": current_user,
                "households": user_households
            }
        )
    except Exception as e:
        logger.error(f"Error loading profile: {e}")
        return templates.TemplateResponse(
            request,
            "auth/profile.html",
            {
                "current_user": current_user,
                "households": []
            }
        )
    finally:
        db.close()


# Settings page
@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """User settings page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "main/settings.html",
        {"current_user": current_user}
    )


# Support page
@router.get("/support", response_class=HTMLResponse)
async def support_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Support and help page."""
    return templates.TemplateResponse(
        request,
        "main/support.html",
        {"current_user": current_user}
    )


# Privacy page
@router.get("/privacy", response_class=HTMLResponse)
async def privacy_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Privacy policy page."""
    return templates.TemplateResponse(
        request,
        "legal/privacy.html",
        {"current_user": current_user}
    )


# Terms page
@router.get("/terms", response_class=HTMLResponse)
async def terms_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Terms of service page."""
    return templates.TemplateResponse(
        request,
        "legal/terms.html",
        {"current_user": current_user}
    )


# About page
@router.get("/about", response_class=HTMLResponse)
async def about_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """About page."""
    return templates.TemplateResponse(
        request,
        "main/about.html",
        {"current_user": current_user}
    )


# ============================================================================
# STATUS AND HEALTH PAGES
# ============================================================================

@router.get("/status", response_class=HTMLResponse)
async def status_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """System status page."""
    return templates.TemplateResponse(
        request,
        "main/status.html",
        {"current_user": current_user}
    )


# ============================================================================
# ERROR PAGES
# ============================================================================

@router.get("/404", response_class=HTMLResponse)
async def not_found_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """404 error page."""
    return templates.TemplateResponse(
        request,
        "errors/404.html",
        {"current_user": current_user}
    )


@router.get("/500", response_class=HTMLResponse)
async def server_error_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """500 error page."""
    return templates.TemplateResponse(
        request,
        "errors/500.html",
        {"current_user": current_user}
    )


# Budgets page
@router.get("/budgets", response_class=HTMLResponse)
async def budgets_list(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Budgets list page."""
    return templates.TemplateResponse(
        request, 
        "placeholder.html",
        {
            "current_user": current_user,
            "config": settings,
            "page_title": "Budgets",
            "page_description": "Budget management feature coming soon!",
            "feature_name": "Budgets"
        }
    )


# Budget create page
@router.get("/budgets/create", response_class=HTMLResponse)
async def budget_create(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Budget create page."""
    return templates.TemplateResponse(
        request, 
        "placeholder.html",
        {
            "current_user": current_user,
            "config": settings,
            "page_title": "Create Budget",
            "page_description": "Budget creation feature coming soon!",
            "feature_name": "Budget Creation"
        }
    )


# Reports page
@router.get("/reports", response_class=HTMLResponse)
async def reports_list(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Reports list page."""
    return templates.TemplateResponse(
        request, 
        "placeholder.html",
        {
            "current_user": current_user,
            "config": settings,
            "page_title": "Reports",
            "page_description": "Advanced reporting features coming soon!",
            "feature_name": "Reports"
        }
    )


# Favicon
@router.get("/favicon.ico")
async def favicon():
    """Serve favicon."""
    return FileResponse("static/icons/favicon.ico")


# Helper function
async def user_needs_onboarding(current_user) -> bool:
    """Check if user needs onboarding."""
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        user_households = await household_service.get_user_households(current_user.id)
        return len(user_households) == 0
    finally:
        db.close()


# Debug endpoint to test dev mode
@router.get("/debug/context", response_class=HTMLResponse)
async def debug_context(
    request: Request,
    current_user: User = Depends(get_current_user_from_cookie_or_header),
):
    """Debug endpoint to check template context."""
    from app.core.template_context import get_dev_context
    import os
    
    dev_context = get_dev_context(request)
    
    debug_html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Debug Context</title></head>
    <body>
        <h1>Debug Context Information</h1>
        <h2>Environment Variables</h2>
        <ul>
            <li>ENVIRONMENT: {os.getenv('ENVIRONMENT', 'NOT_SET')}</li>
            <li>DEBUG: {os.getenv('DEBUG', 'NOT_SET')}</li>
        </ul>
        <h2>Settings</h2>
        <ul>
            <li>settings.debug: {settings.debug}</li>
            <li>settings.environment: {settings.environment}</li>
        </ul>
        <h2>Computed Context</h2>
        <ul>
            <li>dev_mode: {dev_context.get('dev_mode', 'NOT_FOUND')}</li>
            <li>template_name: {dev_context.get('template_name', 'NOT_FOUND')}</li>
        </ul>
        <h2>User Info</h2>
        <ul>
            <li>User: {current_user.email if current_user else 'NOT_AUTHENTICATED'}</li>
            <li>Is Admin: {current_user.is_admin() if current_user else 'N/A'}</li>
            <li>User Role: {current_user.role if current_user else 'N/A'}</li>
        </ul>
        <h2>Full Dev Context</h2>
        <pre>{dev_context}</pre>
    </body>
    </html>
    """
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=debug_html) 