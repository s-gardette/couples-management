"""
Households frontend routes for household-related pages and partials.
"""

import logging
from uuid import UUID
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.modules.auth.dependencies import get_current_user_from_cookie_or_header, get_current_user_optional
from app.modules.expenses.services import HouseholdService
from app.modules.expenses.models.user_household import UserHousehold

router = APIRouter()

# Setup Enhanced Jinja2 templates with automatic global context
from app.core.templates import templates
logger = logging.getLogger(__name__)


async def user_needs_onboarding(current_user) -> bool:
    """Check if user needs onboarding."""
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        user_households = await household_service.get_user_households(current_user.id)
        return len(user_households) == 0
    finally:
        db.close()


@router.get("/households", response_class=HTMLResponse)
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


@router.get("/households/create", response_class=HTMLResponse)
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


@router.get("/households/join", response_class=HTMLResponse)
async def household_join_form(
    request: Request,
    invite_code: str = None,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Join household form page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "expenses/households/join.html",
        {
            "current_user": current_user,
            "invite_code": invite_code
        }
    )


@router.get("/households/{household_id}", response_class=HTMLResponse)
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
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.get("/households/{household_id}/expenses", response_class=HTMLResponse)
async def household_expenses(
    request: Request, 
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Household expenses page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Get household details for the template
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        
        # Check if user has access to this household
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=UUID(household_id)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this household"
            )
        
        # Get household details
        household = await household_service.get_household_with_members(UUID(household_id))
        
        if not household:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Household not found"
            )
        
        return templates.TemplateResponse(
            request,
            "expenses/expenses/list.html",
            {
                "current_user": current_user,
                "household_id": household_id,
                "household": household
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading household expenses page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.get("/households/{household_id}/expenses/create", response_class=HTMLResponse)
async def household_expense_create_form(
    request: Request,
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Household-specific expense creation form page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    logger.info(f"Household-specific expense creation for user: {current_user.id}, household: {household_id}")
    
    # Get user's households (same logic as /expenses/add)
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        
        # Check if user has access to this specific household
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=UUID(household_id)
        )
        
        if not has_permission:
            logger.warning(f"User {current_user.id} denied access to household {household_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this household"
            )
        
        # Get all user households for the selector
        user_households = await household_service.get_user_households(
            user_id=current_user.id,
            include_inactive=False
        )
        
        # Get the specific household details
        target_household = await household_service.get_household_with_members(UUID(household_id))
        
        if not target_household:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Household not found"
            )
        
        logger.info(f"Found {len(user_households)} households, targeting: {target_household.name}")
        logger.info(f"Target household ID: {target_household.id} (type: {type(target_household.id)})")
        
        # Convert households to dictionaries for JSON serialization (same as /expenses/add)
        households_data = []
        for household in user_households:
            household_id_str = str(household.id)
            households_data.append({
                "id": household_id_str,
                "name": household.name,
                "description": household.description,
                "is_active": household.is_active,
                "settings": household.settings
            })
            logger.info(f"Household: {household.name} -> ID: {household_id_str}")
        
        default_household_id = str(target_household.id)
        logger.info(f"Setting default_household_id to: {default_household_id}")
        
        # Use the unified template with the specific household pre-selected
        return templates.TemplateResponse(
            request,
            "expenses/expenses/create.html",
            {
                "current_user": current_user,
                "households": households_data,
                "show_household_selector": len(user_households) > 1,  # Show selector if multiple households
                "default_household_id": default_household_id,  # Ensure consistent UUID string format
                "default_household": target_household
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in household-specific expense creation: {e}", exc_info=True)
        # Fallback to general expense creation
        return RedirectResponse(url="/expenses/add", status_code=status.HTTP_302_FOUND)
    finally:
        db.close()


@router.get("/households/{household_id}/analytics", response_class=HTMLResponse)
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


# ============================================================================
# HOUSEHOLD MEMBER MANAGEMENT (FRONTEND ACTIONS)
# ============================================================================

@router.post("/households/{household_id}/invite-member")
async def invite_member_frontend(
    household_id: str,
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Invite member frontend action."""
    # Implementation would include the full logic from main.py
    return RedirectResponse(url=f"/households/{household_id}", status_code=status.HTTP_302_FOUND)


@router.put("/households/{household_id}/members/{user_id}")
async def update_member_frontend(
    household_id: str,
    user_id: str,
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Update member frontend action."""
    # Implementation would include the full logic from main.py
    return RedirectResponse(url=f"/households/{household_id}", status_code=status.HTTP_302_FOUND)


@router.delete("/households/{household_id}/members/{user_id}")
async def remove_member_frontend(
    household_id: str,
    user_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Remove member frontend action."""
    # Implementation would include the full logic from main.py
    return RedirectResponse(url=f"/households/{household_id}", status_code=status.HTTP_302_FOUND)


# ============================================================================
# HOUSEHOLD PARTIALS (HTMX)
# ============================================================================

@router.get("/partials/households/list", response_class=HTMLResponse)
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


@router.get("/partials/households/create", response_class=HTMLResponse)
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


@router.get("/households/{household_id}/edit", response_class=HTMLResponse)
async def household_edit_form(
    request: Request,
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Household edit form page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        
        # Check if user has access to this household
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=UUID(household_id)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this household"
            )
        
        # Get household details
        household = await household_service.get_household_with_members(UUID(household_id))
        
        if not household:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Household not found"
            )
        
        return templates.TemplateResponse(
            request,
            "expenses/households/edit.html",
            {
                "current_user": current_user,
                "household": household,
                "household_id": household_id
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading household edit form: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.post("/households/{household_id}/delete")
async def delete_household_frontend(
    request: Request,
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Delete household frontend action."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        
        # Check if user has admin access to this household
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=UUID(household_id)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this household"
            )
        
        # TODO: Call API to delete household
        # For now, redirect with success message
        return RedirectResponse(
            url="/households?deleted=1", 
            status_code=status.HTTP_302_FOUND
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting household: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.post("/households/{household_id}/leave")
async def leave_household_frontend(
    request: Request,
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Leave household frontend action."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        
        # Check if user is a member of this household
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=UUID(household_id)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this household"
            )
        
        # TODO: Call API to leave household
        # For now, redirect with success message
        return RedirectResponse(
            url="/households?left=1", 
            status_code=status.HTTP_302_FOUND
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error leaving household: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.get("/partials/households/join", response_class=HTMLResponse)
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