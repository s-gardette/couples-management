"""
API endpoints for expense management.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models.user import User
from app.modules.expenses.services import ExpenseService, HouseholdService, SplittingService
from app.modules.expenses.schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseListResponse,
    ExpenseFilters,
    UpdateExpenseSharesRequest,
    MarkSharePaidRequest,
    ExpenseSummaryResponse,
    ReceiptUploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["expenses"])


def get_expense_service(db: Session = Depends(get_db)) -> ExpenseService:
    """Get expense service instance."""
    return ExpenseService(db)


def get_household_service(db: Session = Depends(get_db)) -> HouseholdService:
    """Get household service instance."""
    return HouseholdService(db)


def get_splitting_service(db: Session = Depends(get_db)) -> SplittingService:
    """Get splitting service instance."""
    return SplittingService(db)


@router.post("/households/{household_id}/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    household_id: UUID,
    expense_data: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    expense_service: ExpenseService = Depends(get_expense_service),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Create a new expense in a household."""
    try:
        # Check if user has access to this household
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=household_id
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this household"
            )
        
        success, message, expense = await expense_service.create_expense(
            household_id=household_id,
            created_by=current_user.id,
            title=expense_data.title,
            description=expense_data.description,
            amount=expense_data.amount,
            currency=expense_data.currency,
            category_id=expense_data.category_id,
            expense_date=expense_data.expense_date,
            tags=expense_data.tags,
            split_method=expense_data.split_method,
            custom_splits=expense_data.split_data
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return expense
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating expense: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create expense"
        )


@router.get("/households/{household_id}/expenses", response_model=ExpenseListResponse)
async def get_household_expenses(
    household_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    created_by: Optional[UUID] = Query(None, description="Filter by creator"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    min_amount: Optional[float] = Query(None, description="Minimum amount"),
    max_amount: Optional[float] = Query(None, description="Maximum amount"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    is_paid: Optional[bool] = Query(None, description="Filter by payment status"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    sort_by: str = Query("expense_date", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    current_user: User = Depends(get_current_user),
    expense_service: ExpenseService = Depends(get_expense_service),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Get expenses for a household with filtering and pagination."""
    try:
        # Check if user has access to this household
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=household_id
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this household"
            )
        
        # Parse filters
        filters = {}
        if category_id:
            filters['category_id'] = category_id
        if created_by:
            filters['created_by'] = created_by
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        if min_amount is not None:
            filters['min_amount'] = min_amount
        if max_amount is not None:
            filters['max_amount'] = max_amount
        if tags:
            filters['tags'] = [tag.strip() for tag in tags.split(',')]
        if is_paid is not None:
            filters['is_paid'] = is_paid
        if search:
            filters['search'] = search
        
        # Calculate skip for pagination
        skip = (page - 1) * per_page
        
        success, message, expenses = await expense_service.get_household_expenses(
            household_id=household_id,
            user_id=current_user.id,
            skip=skip,
            limit=per_page,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Get total count for pagination (we'll need to add this to the service)
        total = len(expenses)  # This is a simplified approach
        
        # Calculate totals
        total_amount = sum(expense.amount for expense in expenses)
        paid_amount = sum(
            expense.amount for expense in expenses 
            if all(share.is_paid for share in expense.shares)
        )
        unpaid_amount = total_amount - paid_amount
        
        return ExpenseListResponse(
            expenses=expenses,
            total=total,
            page=page,
            per_page=per_page,
            total_amount=total_amount,
            paid_amount=paid_amount,
            unpaid_amount=unpaid_amount
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting household expenses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expenses"
        )


@router.get("/expenses/recent", response_model=ExpenseListResponse)
async def get_recent_expenses(
    limit: int = Query(10, ge=1, le=50, description="Number of recent expenses"),
    household_id: Optional[UUID] = Query(None, description="Filter by household"),
    current_user: User = Depends(get_current_user),
    expense_service: ExpenseService = Depends(get_expense_service),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Get recent expenses across all user's households or a specific household."""
    try:
        if household_id:
            # Check if user has access to this specific household
            has_permission = await household_service.check_user_permission(
                user_id=current_user.id,
                household_id=household_id
            )
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this household"
                )
            
            # Get recent expenses for specific household
            success, message, expenses = await expense_service.get_household_expenses(
                household_id=household_id,
                user_id=current_user.id,
                skip=0,
                limit=limit,
                sort_by="created_at",
                sort_order="desc"
            )
        else:
            # Get recent expenses across all user's households
            success, message, expenses = await expense_service.get_user_recent_expenses(
                user_id=current_user.id,
                limit=limit
            )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Calculate totals
        total_amount = sum(expense.amount for expense in expenses)
        paid_amount = sum(
            expense.amount for expense in expenses 
            if hasattr(expense, 'shares') and expense.shares and 
            all(share.is_paid for share in expense.shares)
        )
        unpaid_amount = total_amount - paid_amount
        
        return ExpenseListResponse(
            expenses=expenses,
            total=len(expenses),
            page=1,
            per_page=limit,
            total_amount=total_amount,
            paid_amount=paid_amount,
            unpaid_amount=unpaid_amount
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recent expenses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recent expenses"
        )


@router.get("/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_expense_details(
    expense_id: UUID,
    current_user: User = Depends(get_current_user),
    expense_service: ExpenseService = Depends(get_expense_service),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Get detailed expense information."""
    try:
        success, message, expense = await expense_service.get_expense_details(
            expense_id=expense_id,
            user_id=current_user.id
        )
        
        if not success:
            if "not found" in message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=message
                )
        
        return expense
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting expense details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expense details"
        )


@router.put("/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: UUID,
    expense_data: ExpenseUpdate,
    recalculate_splits: bool = Query(False, description="Recalculate expense splits"),
    current_user: User = Depends(get_current_user),
    expense_service: ExpenseService = Depends(get_expense_service)
):
    """Update an expense."""
    try:
        success, message, expense = await expense_service.update_expense(
            expense_id=expense_id,
            user_id=current_user.id,
            updates=expense_data.model_dump(exclude_unset=True),
            recalculate_splits=recalculate_splits
        )
        
        if not success:
            if "not found" in message.lower() or "access" in message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message
                )
        
        return expense
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating expense: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update expense"
        )


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: UUID,
    current_user: User = Depends(get_current_user),
    expense_service: ExpenseService = Depends(get_expense_service)
):
    """Delete an expense (soft delete)."""
    try:
        success, message = await expense_service.delete_expense(
            expense_id=expense_id,
            user_id=current_user.id
        )
        
        if not success:
            if "not found" in message.lower() or "access" in message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message
                )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting expense: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete expense"
        )


@router.post("/expenses/{expense_id}/receipt", response_model=ReceiptUploadResponse)
async def upload_receipt(
    expense_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    expense_service: ExpenseService = Depends(get_expense_service)
):
    """Upload a receipt for an expense."""
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/gif", "application/pdf"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only JPEG, PNG, GIF, and PDF files are allowed."
            )
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size too large. Maximum size is 10MB."
            )
        
        success, message, receipt_url = await expense_service.upload_receipt(
            expense_id=expense_id,
            user_id=current_user.id,
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type
        )
        
        if not success:
            if "not found" in message.lower() or "access" in message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message
                )
        
        return ReceiptUploadResponse(
            receipt_url=receipt_url,
            expense_id=expense_id,
            uploaded_at=datetime.utcnow(),
            file_size=len(file_content),
            file_type=file.content_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading receipt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload receipt"
        )


@router.put("/expenses/{expense_id}/shares", response_model=ExpenseResponse)
async def update_expense_shares(
    expense_id: UUID,
    shares_data: UpdateExpenseSharesRequest,
    current_user: User = Depends(get_current_user),
    splitting_service: SplittingService = Depends(get_splitting_service)
):
    """Update expense shares/splits."""
    try:
        success, message, expense = await splitting_service.update_expense_splits(
            expense_id=expense_id,
            user_id=current_user.id,
            split_method=shares_data.split_method,
            split_data=shares_data.split_data,
            recalculate_existing=shares_data.recalculate_existing
        )
        
        if not success:
            if "not found" in message.lower() or "access" in message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message
                )
        
        return expense
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating expense shares: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update expense shares"
        )


@router.post("/expenses/{expense_id}/shares/{user_id}/pay", status_code=status.HTTP_200_OK)
async def mark_share_paid(
    expense_id: UUID,
    user_id: UUID,
    payment_data: MarkSharePaidRequest,
    current_user: User = Depends(get_current_user),
    splitting_service: SplittingService = Depends(get_splitting_service)
):
    """Mark an expense share as paid."""
    try:
        success, message = await splitting_service.mark_share_paid(
            expense_id=expense_id,
            user_id=user_id,
            paid_by=current_user.id,
            payment_method=payment_data.payment_method,
            payment_notes=payment_data.payment_notes
        )
        
        if not success:
            if "not found" in message.lower() or "access" in message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message
                )
        
        return {"message": message}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking share as paid: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark share as paid"
        )


@router.delete("/expenses/{expense_id}/shares/{user_id}/pay", status_code=status.HTTP_200_OK)
async def mark_share_unpaid(
    expense_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    splitting_service: SplittingService = Depends(get_splitting_service)
):
    """Mark an expense share as unpaid."""
    try:
        success, message = await splitting_service.mark_share_unpaid(
            expense_id=expense_id,
            user_id=user_id,
            updated_by=current_user.id
        )
        
        if not success:
            if "not found" in message.lower() or "access" in message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message
                )
        
        return {"message": message}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking share as unpaid: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark share as unpaid"
        )


@router.get("/households/{household_id}/expenses/summary", response_model=ExpenseSummaryResponse)
async def get_expense_summary(
    household_id: UUID,
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    expense_service: ExpenseService = Depends(get_expense_service),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Get expense summary for a household."""
    try:
        # Check if user has access to this household
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=household_id
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this household"
            )
        
        # Parse date filters
        start_date = None
        end_date = None
        if date_from:
            try:
                start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_from format. Use YYYY-MM-DD"
                )
        if date_to:
            try:
                end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_to format. Use YYYY-MM-DD"
                )
        
        success, message, summary = await expense_service.get_expense_summary(
            household_id=household_id,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting expense summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expense summary"
        ) 