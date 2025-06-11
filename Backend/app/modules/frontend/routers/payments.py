"""
Payments frontend routes for payment-related pages and partials.
"""

import logging
from decimal import Decimal
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.config import settings
from app.database import get_db
from app.modules.auth.dependencies import get_current_user_from_cookie_or_header
from app.modules.expenses.models.payment import Payment
from app.modules.expenses.services.payment_service import PaymentService

router = APIRouter()

# Setup Enhanced Jinja2 templates with automatic global context
from app.core.templates import templates
logger = logging.getLogger(__name__)


def get_payment_service(db: Session = Depends(get_db)) -> PaymentService:
    """Get payment service instance."""
    return PaymentService(db)


@router.get("/payments/history", response_class=HTMLResponse)
async def payment_history_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header),
    db: Session = Depends(get_db)
):
    """Payment history page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Calculate payment summary for the current user
    summary = {
        "total_paid": Decimal("0.00"),
        "total_received": Decimal("0.00")
    }
    
    if current_user:
        # Calculate total paid (where user is the payer)
        total_paid = (
            db.query(func.sum(Payment.amount))
            .filter(
                Payment.payer_id == current_user.id,
                Payment.is_active == True
            )
            .scalar()
        ) or Decimal("0.00")
        
        # Calculate total received (where user is the payee)
        total_received = (
            db.query(func.sum(Payment.amount))
            .filter(
                Payment.payee_id == current_user.id,
                Payment.is_active == True
            )
            .scalar()
        ) or Decimal("0.00")
        
        summary = {
            "total_paid": Decimal(str(total_paid)),
            "total_received": Decimal(str(total_received))
        }
    
    return templates.TemplateResponse(
        request,
        "expenses/payments/history.html",
        {
            "current_user": current_user,
            "summary": summary
        }
    )


@router.get("/payments/create", response_class=HTMLResponse)
async def payment_create_page(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Payment creation page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        request,
        "expenses/payments/create.html",
        {"current_user": current_user}
    )


@router.get("/households/{household_id}/payments/create", response_class=HTMLResponse)
async def household_payment_create_page(
    request: Request,
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Household-specific payment creation page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        request,
        "expenses/payments/create.html",
        {
            "current_user": current_user,
            "household_id": household_id
        }
    )


# ============================================================================
# PAYMENT PARTIALS (HTMX)
# ============================================================================

@router.get("/partials/payments/history", response_class=HTMLResponse)
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
    
    # Implementation would include the full logic from main.py
    return templates.TemplateResponse(
        request,
        "partials/payments/history.html",
        {
            "current_user": current_user,
            "household_id": household_id,
            "page": page,
            "per_page": per_page
        }
    )


@router.get("/partials/payments/{payment_id}/details", response_class=HTMLResponse)
async def payment_details_partial(
    request: Request,
    payment_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Payment details partial for HTMX modal loading."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    return templates.TemplateResponse(
        request,
        "partials/payments/details.html",
        {
            "current_user": current_user,
            "payment_id": payment_id
        }
    )


@router.get("/partials/payments/{payment_id}/edit", response_class=HTMLResponse)
async def payment_edit_partial(
    request: Request,
    payment_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Payment edit partial for HTMX modal loading."""
    if settings.require_authentication_for_all and not current_user:
        return HTMLResponse("<div class='text-red-500'>Authentication required</div>", status_code=401)
    
    return templates.TemplateResponse(
        request,
        "partials/payments/edit.html",
        {
            "current_user": current_user,
            "payment_id": payment_id
        }
    )


# ============================================================================
# EXPENSE SHARE PAYMENT ACTIONS
# ============================================================================

@router.post("/expenses/{expense_id}/shares/{user_id}/pay")
async def mark_expense_share_paid_frontend(
    request: Request,
    expense_id: str,
    user_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Mark expense share as paid frontend action."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    # TODO: Call API to mark share as paid
    # For now, redirect back to expense details
    return RedirectResponse(
        url=f"/expenses/{expense_id}?paid=1", 
        status_code=302
    )


@router.post("/expenses/{expense_id}/shares/{user_id}/unpay")
async def mark_expense_share_unpaid_frontend(
    request: Request,
    expense_id: str,
    user_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Mark expense share as unpaid frontend action."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    # TODO: Call API to mark share as unpaid
    # For now, redirect back to expense details
    return RedirectResponse(
        url=f"/expenses/{expense_id}?unpaid=1", 
        status_code=302
    )


# ============================================================================
# CATEGORY MANAGEMENT
# ============================================================================

@router.get("/households/{household_id}/categories", response_class=HTMLResponse)
async def categories_management(
    request: Request,
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Categories management page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        request,
        "expenses/categories/list.html",
        {
            "current_user": current_user,
            "household_id": household_id
        }
    )


@router.get("/households/{household_id}/categories/create", response_class=HTMLResponse)
async def category_create_form(
    request: Request,
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Create category form page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        request,
        "expenses/categories/create.html",
        {
            "current_user": current_user,
            "household_id": household_id
        }
    )


@router.get("/categories/{category_id}/edit", response_class=HTMLResponse)
async def category_edit_form(
    request: Request,
    category_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Edit category form page."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        request,
        "expenses/categories/edit.html",
        {
            "current_user": current_user,
            "category_id": category_id
        }
    )


@router.post("/categories/{category_id}/delete")
async def delete_category_frontend(
    request: Request,
    category_id: str,
    household_id: str = None,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Delete category frontend action."""
    if settings.require_authentication_for_all and not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    # TODO: Call API to delete category
    # For now, redirect back to categories list
    redirect_url = f"/households/{household_id}/categories?deleted=1" if household_id else "/households"
    return RedirectResponse(
        url=redirect_url, 
        status_code=302
    ) 