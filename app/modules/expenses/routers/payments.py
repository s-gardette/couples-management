"""
API endpoints for payment management.
"""

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models.user import User
from app.modules.expenses.services.payment_service import PaymentService
from app.modules.expenses.services.reimbursement_service import ReimbursementService
from app.modules.expenses.schemas.payment_schemas import (
    PaymentCreate,
    PaymentUpdate,
    PaymentFilters,
    PaymentResponse,
    PaymentListResponse,
    LinkExpenseShareRequest,
    LinkExpenseShareResponse,
    DirectExpenseReimbursementRequest,
    BulkExpensePaymentRequest,
    GeneralPaymentRequest,
    ReimbursementResponse,
    UnpaidExpensesResponse,
)

router = APIRouter(prefix="/payments", tags=["payments"])


def get_payment_service(db: Session = Depends(get_db)) -> PaymentService:
    """Get payment service instance."""
    return PaymentService(db)


def get_reimbursement_service(db: Session = Depends(get_db)) -> ReimbursementService:
    """Get reimbursement service instance."""
    return ReimbursementService(db)


@router.post("/", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service)
) -> PaymentResponse:
    """
    Create a new payment.
    
    Creates a payment between two users in a household.
    """
    success, message, payment = await payment_service.create_payment(
        household_id=payment_data.household_id,
        payer_id=payment_data.payer_id,
        payee_id=payment_data.payee_id,
        amount=payment_data.amount,
        payment_type=payment_data.payment_type,
        current_user_id=current_user.id,
        currency=payment_data.currency,
        payment_method=payment_data.payment_method,
        description=payment_data.description,
        reference_number=payment_data.reference_number,
        payment_date=payment_data.payment_date
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return PaymentResponse.from_orm(payment)


@router.get("/", response_model=PaymentListResponse)
async def get_payments(
    household_id: UUID,
    filters: PaymentFilters = Depends(),
    current_user: User = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service)
) -> PaymentListResponse:
    """
    Get payments with filtering and pagination.
    
    Retrieves payments for a household with various filtering options.
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
    
    return PaymentListResponse(
        payments=[PaymentResponse.from_orm(payment) for payment in result["payments"]],
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        total_pages=result["total_pages"]
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service)
) -> PaymentResponse:
    """
    Get a specific payment by ID.
    
    Retrieves detailed information about a payment including linked expense shares.
    """
    success, message, payment = await payment_service.get_payment_by_id(
        payment_id=payment_id,
        current_user_id=current_user.id
    )
    
    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        elif "permission" in message.lower():
            raise HTTPException(status_code=403, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    return PaymentResponse.from_orm(payment)


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: UUID,
    payment_update: PaymentUpdate,
    current_user: User = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service)
) -> PaymentResponse:
    """
    Update a payment.
    
    Updates payment details. Only household members can update payments.
    """
    # Convert to dict and remove None values
    updates = {k: v for k, v in payment_update.dict().items() if v is not None}
    
    success, message, payment = await payment_service.update_payment(
        payment_id=payment_id,
        current_user_id=current_user.id,
        updates=updates
    )
    
    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        elif "permission" in message.lower():
            raise HTTPException(status_code=403, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    return PaymentResponse.from_orm(payment)


@router.delete("/{payment_id}")
async def delete_payment(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service)
) -> Dict[str, str]:
    """
    Delete a payment.
    
    Soft deletes a payment and its associated expense share links.
    """
    success, message = await payment_service.delete_payment(
        payment_id=payment_id,
        current_user_id=current_user.id
    )
    
    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        elif "permission" in message.lower():
            raise HTTPException(status_code=403, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


@router.post("/{payment_id}/link-expense-share", response_model=LinkExpenseShareResponse)
async def link_expense_share(
    payment_id: UUID,
    link_request: LinkExpenseShareRequest,
    current_user: User = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service)
) -> LinkExpenseShareResponse:
    """
    Link a payment to an expense share.
    
    Allocates part of a payment to cover an expense share.
    """
    success, message, esp = await payment_service.link_expense_share(
        payment_id=payment_id,
        expense_share_id=link_request.expense_share_id,
        amount=link_request.amount,
        current_user_id=current_user.id
    )
    
    return LinkExpenseShareResponse(
        success=success,
        message=message,
        expense_share_payment_id=esp.id if esp else None
    )


@router.delete("/{payment_id}/unlink-expense-share/{expense_share_id}")
async def unlink_expense_share(
    payment_id: UUID,
    expense_share_id: UUID,
    current_user: User = Depends(get_current_user),
    payment_service: PaymentService = Depends(get_payment_service)
) -> Dict[str, str]:
    """
    Unlink a payment from an expense share.
    
    Removes the allocation between a payment and expense share.
    """
    success, message = await payment_service.unlink_expense_share(
        payment_id=payment_id,
        expense_share_id=expense_share_id,
        current_user_id=current_user.id
    )
    
    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        elif "permission" in message.lower():
            raise HTTPException(status_code=403, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# Reimbursement workflow endpoints
@router.post("/reimbursements/expense", response_model=ReimbursementResponse)
async def reimburse_expense_directly(
    request: DirectExpenseReimbursementRequest,
    current_user: User = Depends(get_current_user),
    reimbursement_service: ReimbursementService = Depends(get_reimbursement_service)
) -> ReimbursementResponse:
    """
    Reimburse a specific expense directly.
    
    Workflow 1: Creates a payment that covers all shares of the expense and marks it as paid.
    """
    success, message, payment = await reimbursement_service.reimburse_expense_directly(
        expense_id=request.expense_id,
        payer_id=request.payer_id,
        current_user_id=current_user.id,
        payment_method=request.payment_method,
        description=request.description,
        reference_number=request.reference_number
    )
    
    return ReimbursementResponse(
        success=success,
        message=message,
        payment=PaymentResponse.from_orm(payment) if payment else None
    )


@router.post("/reimbursements/bulk", response_model=ReimbursementResponse)
async def pay_all_user_expenses(
    request: BulkExpensePaymentRequest,
    current_user: User = Depends(get_current_user),
    reimbursement_service: ReimbursementService = Depends(get_reimbursement_service)
) -> ReimbursementResponse:
    """
    Pay all unpaid expenses for a user.
    
    Workflow 2: Creates a single payment that covers all unpaid expenses for the target user.
    """
    success, message, payment = await reimbursement_service.pay_all_user_expenses(
        household_id=request.household_id,
        target_user_id=request.target_user_id,
        payer_id=request.payer_id,
        current_user_id=current_user.id,
        payment_method=request.payment_method,
        description=request.description,
        reference_number=request.reference_number
    )
    
    return ReimbursementResponse(
        success=success,
        message=message,
        payment=PaymentResponse.from_orm(payment) if payment else None
    )


@router.post("/reimbursements/general", response_model=ReimbursementResponse)
async def make_general_payment(
    request: GeneralPaymentRequest,
    current_user: User = Depends(get_current_user),
    reimbursement_service: ReimbursementService = Depends(get_reimbursement_service)
) -> ReimbursementResponse:
    """
    Make a general payment with optional expense allocations.
    
    Workflow 3: Creates a payment for a specified amount, optionally linking it to expense shares.
    """
    # Convert expense allocations to the format expected by the service
    expense_allocations = None
    if request.expense_allocations:
        expense_allocations = [
            {
                "expense_share_id": alloc.expense_share_id,
                "amount": alloc.amount
            }
            for alloc in request.expense_allocations
        ]
    
    success, message, payment = await reimbursement_service.make_general_payment(
        household_id=request.household_id,
        payer_id=request.payer_id,
        payee_id=request.payee_id,
        amount=request.amount,
        current_user_id=current_user.id,
        expense_allocations=expense_allocations,
        payment_method=request.payment_method,
        description=request.description,
        reference_number=request.reference_number
    )
    
    return ReimbursementResponse(
        success=success,
        message=message,
        payment=PaymentResponse.from_orm(payment) if payment else None
    )


@router.get("/unpaid-expenses/{household_id}/{user_id}", response_model=UnpaidExpensesResponse)
async def get_unpaid_expenses_for_user(
    household_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    reimbursement_service: ReimbursementService = Depends(get_reimbursement_service)
) -> UnpaidExpensesResponse:
    """
    Get all unpaid expenses for a specific user.
    
    Returns a list of expenses that the user still owes money for.
    """
    success, message, result = await reimbursement_service.get_unpaid_expenses_for_user(
        household_id=household_id,
        user_id=user_id,
        current_user_id=current_user.id
    )
    
    if not success:
        if "not found" in message.lower() or "not a member" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        elif "permission" in message.lower():
            raise HTTPException(status_code=403, detail=message)
        else:
            raise HTTPException(status_code=400, detail=message)
    
    return UnpaidExpensesResponse(**result) 