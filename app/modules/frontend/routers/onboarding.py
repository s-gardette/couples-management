"""
Onboarding frontend routes for user onboarding flow.
"""

import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse


from app.config import settings
from app.modules.auth.dependencies import get_current_user_from_cookie_or_header

router = APIRouter()

# Setup Enhanced Jinja2 templates with automatic global context
from app.core.templates import templates
logger = logging.getLogger(__name__)


@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding_welcome(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Onboarding welcome page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        request,
        "onboarding/welcome.html",
        {"current_user": current_user}
    )


@router.get("/onboarding/create-household", response_class=HTMLResponse)
async def onboarding_create_household(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Onboarding create household page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        request,
        "onboarding/create_household.html",
        {"current_user": current_user}
    )


@router.get("/onboarding/add-members", response_class=HTMLResponse)
async def onboarding_add_members(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Onboarding add members page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        request,
        "onboarding/add_members.html",
        {"current_user": current_user}
    )


@router.get("/onboarding/join-household", response_class=HTMLResponse)
async def onboarding_join_household(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Onboarding join household page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        request,
        "onboarding/join_household.html",
        {"current_user": current_user}
    )


@router.get("/onboarding/complete", response_class=HTMLResponse)
async def onboarding_complete(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Onboarding complete page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        request,
        "onboarding/complete.html",
        {"current_user": current_user}
    ) 