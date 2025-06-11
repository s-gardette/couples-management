"""
Auth frontend routes for authentication-related pages and functionality.
"""

import logging
from uuid import UUID
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.modules.auth.dependencies import get_current_user_optional, get_current_user_from_cookie_or_header
from app.modules.expenses.models.user_household import UserHousehold
from app.modules.expenses.models.household import Household, UserHouseholdRole

router = APIRouter()

# Setup Enhanced Jinja2 templates with automatic global context
from app.core.templates import templates
logger = logging.getLogger(__name__)


# ============================================================================
# HOUSEHOLD JOIN FUNCTIONALITY (AUTH FLOW)
# ============================================================================

@router.get("/join")
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


@router.post("/join")
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
        existing_membership = db.query(UserHousehold).filter(
            UserHousehold.household_id == household.id,
            UserHousehold.user_id == current_user.id
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
                    setTimeout(() => window.location.href = '/households/{household.id}', 2000);
                </script>
                """
            )
        
        # Add user as a member using the UserHousehold model
        new_membership = UserHousehold(
            user_id=current_user.id,
            household_id=household.id,
            role=UserHouseholdRole.MEMBER,
            nickname=None,
            is_active=True
        )
        db.add(new_membership)
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