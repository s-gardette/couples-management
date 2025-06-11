"""
Expenses frontend routes for expense-related pages and partials.
"""

import logging
from uuid import UUID
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.modules.auth.dependencies import get_current_user_from_cookie_or_header
from app.modules.expenses.services import HouseholdService
from app.modules.expenses.services.expense_service import ExpenseService
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


@router.get("/expenses", response_class=HTMLResponse)
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


@router.get("/expenses/dashboard", response_class=HTMLResponse)
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


@router.get("/expenses/list", response_class=HTMLResponse)
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


@router.get("/expenses/create", response_class=HTMLResponse)
async def expense_create_form(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Expense creation form page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request,
        "expenses/expenses/create.html",
        {"current_user": current_user}
    )


@router.get("/expenses/add", response_class=HTMLResponse)
async def expense_add_form(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Expense creation form with household selection."""
    if settings.require_authentication_for_all and not current_user:
        logger.warning("No current user found for expense creation")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    logger.info(f"Expense creation request for user: {current_user.id} ({current_user.username})")
    
    # Get user's households to choose from
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        user_households = await household_service.get_user_households(
            user_id=current_user.id,
            include_inactive=False
        )
        
        logger.info(f"Found {len(user_households)} households for user {current_user.id}")
        for household in user_households:
            logger.info(f"  - Household: {household.id} ({household.name})")
        
        # If user has no households, redirect to onboarding
        if not user_households:
            logger.warning(f"User {current_user.id} has no households, redirecting to onboarding")
            return RedirectResponse(url="/onboarding", status_code=status.HTTP_302_FOUND)
        
        # Prepare household data for the form
        households_data = []
        for household in user_households:
            households_data.append({
                "id": str(household.id),
                "name": household.name,
                "description": household.description or "",
                "member_count": len(household.members) if hasattr(household, 'members') else 0
            })
        
        logger.info(f"User has {len(user_households)} households available")
        
        # Show the creation form with household selection embedded
        # Let the frontend JavaScript handle default household selection from localStorage
        return templates.TemplateResponse(
            request,
            "expenses/expenses/create.html",
            {
                "current_user": current_user,
                "households": households_data,
                "show_household_selector": len(user_households) > 1,  # Only show selector if multiple households
                "default_household_id": None,  # Let frontend handle default selection
                "default_household": None
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting user households for expense creation: {e}", exc_info=True)
        # Instead of redirecting to onboarding, let's show a debug page
        return templates.TemplateResponse(
            request,
            "expenses/expenses/create.html",
            {
                "current_user": current_user,
                "households": [],
                "show_household_selector": False,
                "default_household_id": None,
                "default_household": None,
                "error": str(e)
            }
        )
    finally:
        db.close()


@router.get("/expenses/create_modal", response_class=HTMLResponse)
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


@router.get("/expenses/{expense_id}", response_class=HTMLResponse)
async def expense_detail_page(
    request: Request,
    expense_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Expense detail page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    db = next(get_db())
    try:
        expense_service = ExpenseService(db)
        
        # Get expense details
        success, message, expense = await expense_service.get_expense_details(
            expense_id=UUID(expense_id),
            user_id=current_user.id
        )
        
        if not success:
            if "not found" in message.lower():
                raise HTTPException(status_code=404, detail="Expense not found")
            else:
                raise HTTPException(status_code=403, detail="Access denied")
        
        return templates.TemplateResponse(
            request,
            "expenses/expenses/detail.html",
            {
                "current_user": current_user,
                "expense": expense
            }
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expense ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading expense details: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.get("/analytics", response_class=HTMLResponse)
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


# ============================================================================
# EXPENSE PARTIALS (HTMX)
# ============================================================================

@router.get("/partials/expenses/recent", response_class=HTMLResponse)
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
    
    # Implementation would continue here with the full logic from main.py
    return templates.TemplateResponse(
        request,
        "partials/expenses/recent.html",
        {
            "current_user": current_user,
            "limit": limit,
            "household_id": household_id
        }
    )


@router.get("/partials/expenses/create", response_class=HTMLResponse)
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


@router.get("/partials/expenses/{expense_id}/details", response_class=HTMLResponse)
async def expense_details_partial(
    request: Request,
    expense_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Expense details partial for modal display."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    db = next(get_db())
    try:
        expense_service = ExpenseService(db)
        
        # Get expense details
        success, message, expense = await expense_service.get_expense_details(
            expense_id=UUID(expense_id),
            user_id=current_user.id
        )
        
        if not success:
            return HTMLResponse(f"<div class='text-red-500'>Error: {message}</div>", status_code=404)
        
        return templates.TemplateResponse(
            request,
            "partials/expenses/details.html",
            {
                "current_user": current_user,
                "expense": expense
            }
        )
        
    except ValueError:
        return HTMLResponse("<div class='text-red-500'>Invalid expense ID</div>", status_code=400)
    except Exception as e:
        logger.error(f"Error loading expense details partial: {e}")
        return HTMLResponse("<div class='text-red-500'>Internal server error</div>", status_code=500)
    finally:
        db.close()


@router.get("/partials/expenses/unpaid", response_class=HTMLResponse)
async def unpaid_expenses_partial(
    request: Request,
    household_id: str = None,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Unpaid expenses partial for HTMX loading."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    return templates.TemplateResponse(
        request,
        "partials/expenses/unpaid.html",
        {
            "current_user": current_user,
            "household_id": household_id
        }
    )


@router.get("/partials/expenses/user-summary", response_class=HTMLResponse)
async def user_expenses_summary_partial(
    request: Request,
    payee_id: str,
    household_id: str = None,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """User expenses summary partial for HTMX loading."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    return templates.TemplateResponse(
        request,
        "partials/expenses/user_summary.html",
        {
            "current_user": current_user,
            "payee_id": payee_id,
            "household_id": household_id
        }
    )


@router.get("/partials/expenses/linkable", response_class=HTMLResponse)
async def linkable_expenses_partial(
    request: Request,
    household_id: str = None,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Linkable expenses partial for HTMX loading."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    return templates.TemplateResponse(
        request,
        "partials/expenses/linkable.html",
        {
            "current_user": current_user,
            "household_id": household_id
        }
    )


@router.get("/expenses/{expense_id}/edit", response_class=HTMLResponse)
async def expense_edit_form(
    request: Request,
    expense_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Expense edit form."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    db = next(get_db())
    try:
        expense_service = ExpenseService(db)
        household_service = HouseholdService(db)
        
        # Get expense details
        success, message, expense = await expense_service.get_expense_details(
            expense_id=UUID(expense_id),
            user_id=current_user.id
        )
        
        if not success:
            if "not found" in message.lower():
                raise HTTPException(status_code=404, detail="Expense not found")
            else:
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Get user's households for the form
        user_households = await household_service.get_user_households(
            user_id=current_user.id,
            include_inactive=False
        )
        
        # Prepare household data
        households_data = []
        for household in user_households:
            households_data.append({
                "id": str(household.id),
                "name": household.name,
                "description": household.description or "",
                "member_count": len(household.members) if hasattr(household, 'members') else 0
            })
        
        # Create expense data for JavaScript serialization
        expense_js_data = {
            "id": str(expense.id),
            "title": expense.title,
            "description": expense.description or "",
            "amount": float(expense.amount),  # Convert Decimal to float for JavaScript
            "currency": expense.currency,
            "expense_date": expense.expense_date.strftime("%Y-%m-%d"),
            "category_id": str(expense.category_id) if expense.category_id else "",
            "tags": expense.tags or [],
            "household_id": str(expense.household_id),
            "created_by": str(expense.created_by),
            "receipt_url": expense.receipt_url
        }
        
        return templates.TemplateResponse(
            request,
            "expenses/expenses/edit.html",
            {
                "current_user": current_user,
                "expense": expense,  # Pass the original expense object with relationships
                "expense_js_data": expense_js_data,  # Pass the JavaScript-safe data
                "households": households_data,
                "show_household_selector": len(user_households) > 1
            }
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expense ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading expense edit form: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.post("/expenses/{expense_id}/delete")
async def delete_expense_frontend(
    request: Request,
    expense_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Delete expense frontend action."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    db = next(get_db())
    try:
        expense_service = ExpenseService(db)
        
        # Get expense details first to get household_id for redirect
        success, message, expense = await expense_service.get_expense_details(
            expense_id=UUID(expense_id),
            user_id=current_user.id
        )
        
        if not success:
            if "not found" in message.lower():
                raise HTTPException(status_code=404, detail="Expense not found")
            else:
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete the expense (this should call the service method that calls the API)
        # For now, we'll redirect with a success message
        household_id = expense.household_id
        
        # Add success message to session/flash
        return RedirectResponse(
            url=f"/households/{household_id}/expenses?deleted=1", 
            status_code=status.HTTP_302_FOUND
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting expense: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.get("/expenses/{expense_id}/receipt", response_class=HTMLResponse)
async def expense_receipt_upload_form(
    request: Request,
    expense_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Receipt upload form page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    db = next(get_db())
    try:
        expense_service = ExpenseService(db)
        
        # Get expense details to verify access
        success, message, expense = await expense_service.get_expense_details(
            expense_id=UUID(expense_id),
            user_id=current_user.id
        )
        
        if not success:
            if "not found" in message.lower():
                raise HTTPException(status_code=404, detail="Expense not found")
            else:
                raise HTTPException(status_code=403, detail="Access denied")
        
        return templates.TemplateResponse(
            request,
            "expenses/expenses/receipt.html",
            {
                "current_user": current_user,
                "expense": expense,
                "expense_id": expense_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading receipt upload form: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.post("/expenses/{expense_id}/receipt")
async def upload_expense_receipt_frontend(
    request: Request,
    expense_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Upload receipt frontend action."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # TODO: Handle file upload and call API
    # For now, redirect back to expense details
    return RedirectResponse(
        url=f"/expenses/{expense_id}?receipt_uploaded=1", 
        status_code=status.HTTP_302_FOUND
    )


@router.get("/debug/households", response_class=HTMLResponse)
async def debug_households(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Debug route to check household loading."""
    if not current_user:
        return HTMLResponse("<div>No current user</div>")
    
    db = next(get_db())
    try:
        household_service = HouseholdService(db)
        
        # Test the actual query
        user_households = await household_service.get_user_households(
            user_id=current_user.id,
            include_inactive=False
        )
        
        # Also test with inactive included
        all_households = await household_service.get_user_households(
            user_id=current_user.id,
            include_inactive=True
        )
        
        # Test direct database query
        from app.modules.expenses.models.user_household import UserHousehold
        from app.modules.expenses.models.household import Household
        
        direct_query = (
            db.query(Household)
            .join(UserHousehold)
            .filter(UserHousehold.user_id == current_user.id)
            .all()
        )
        
        html = f"""
        <html>
        <head><title>Debug Households</title></head>
        <body>
            <h1>Debug Household Loading</h1>
            <h2>Current User</h2>
            <p>ID: {current_user.id}</p>
            <p>Username: {current_user.username}</p>
            <p>Email: {current_user.email}</p>
            
            <h2>Active Households (via service)</h2>
            <p>Count: {len(user_households)}</p>
            <ul>
            {''.join([f'<li>{h.id} - {h.name} (active: {h.is_active})</li>' for h in user_households])}
            </ul>
            
            <h2>All Households (via service)</h2>
            <p>Count: {len(all_households)}</p>
            <ul>
            {''.join([f'<li>{h.id} - {h.name} (active: {h.is_active})</li>' for h in all_households])}
            </ul>
            
            <h2>Direct Database Query</h2>
            <p>Count: {len(direct_query)}</p>
            <ul>
            {''.join([f'<li>{h.id} - {h.name} (active: {h.is_active})</li>' for h in direct_query])}
            </ul>
        </body>
        </html>
        """
        
        return HTMLResponse(html)
        
    except Exception as e:
        return HTMLResponse(f"<div>Error: {str(e)}</div>")
    finally:
        db.close() 