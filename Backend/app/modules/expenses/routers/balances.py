"""
API endpoints for balance and payment analytics.
"""

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models.user import User
from app.modules.expenses.services.payment_service import PaymentService
from app.modules.expenses.schemas.payment_schemas import (
    PaymentFilters,
    BalanceSummary,
    PaymentHistoryResponse,
    UserPaymentSummary,
)

router = APIRouter(prefix="/balances", tags=["balances"])


def get_payment_service(db: Session = Depends(get_db)) -> PaymentService:
    """Get payment service instance."""
    return PaymentService(db)


@router.get("/households/{household_id}", response_model=BalanceSummary)
async def get_household_balance_summary(
    household_id: UUID,
    current_user: User = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service)
) -> BalanceSummary:
    """
    Get balance summary for a household.
    
    Shows who owes whom and how much across all household members.
    """
    # TODO: Implement BalanceService to calculate comprehensive balances
    # For now, return a placeholder response
    raise HTTPException(
        status_code=501, 
        detail="Balance calculations not yet implemented. This endpoint will be available after BalanceService integration."
    )


@router.get("/households/{household_id}/payment-history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    household_id: UUID,
    filters: PaymentFilters = Depends(),
    current_user: User = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service)
) -> PaymentHistoryResponse:
    """
    Get payment history for a household with filtering.
    
    Returns payments with details about related expenses.
    """
    success, message, result = await payment_service.get_payments(
        household_id=household_id,
        current_user_id=current_user.id,
        page=filters.page,
        per_page=filters.per_page,
        payer_id=filters.payer_id,
        payee_id=filters.payee_id,
        payment_type=filters.payment_type,
        payment_method=filters.payment_method,
        start_date=filters.start_date,
        end_date=filters.end_date,
        min_amount=filters.min_amount,
        max_amount=filters.max_amount,
        search=filters.search,
        sort_by=filters.sort_by,
        sort_order=filters.sort_order
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    # Build payment history with related expenses
    from app.modules.expenses.schemas.payment_schemas import PaymentHistoryEntry, PaymentResponse, ExpenseShareSummary
    
    payment_entries = []
    for payment in result["payments"]:
        # Get related expense shares
        related_expenses = []
        for esp in payment.expense_share_payments:
            if esp.is_active and esp.expense_share:
                related_expenses.append(ExpenseShareSummary(
                    id=esp.expense_share.id,
                    expense_id=esp.expense_share.expense_id,
                    expense_title=esp.expense_share.expense.title if esp.expense_share.expense else "Unknown",
                    share_amount=esp.expense_share.share_amount,
                    allocated_amount=esp.amount
                ))
        
        payment_entries.append(PaymentHistoryEntry(
            payment=PaymentResponse.from_orm(payment),
            related_expenses=related_expenses
        ))
    
    return PaymentHistoryResponse(
        household_id=household_id,
        payments=payment_entries,
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        total_pages=result["total_pages"]
    )


@router.get("/users/{user_id}/summary", response_model=UserPaymentSummary)
async def get_user_payment_summary(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service)
) -> UserPaymentSummary:
    """
    Get payment summary for a specific user.
    
    Shows totals paid and received, with recent payment activity.
    """
    # TODO: Implement user-specific payment summaries
    # For now, return a placeholder response
    raise HTTPException(
        status_code=501,
        detail="User payment summaries not yet implemented. This endpoint will be available after enhanced analytics implementation."
    ) 