"""
Dependencies for the expenses module.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models.user import User
from app.modules.expenses.services import HouseholdService
from app.modules.expenses.models import Household, UserHousehold


async def get_household_or_404(
    household_id: UUID,
    db: Session = Depends(get_db)
) -> Household:
    """Get household by ID or raise 404."""
    household = db.query(Household).filter(
        Household.id == household_id,
        Household.is_active == True
    ).first()
    
    if not household:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household not found"
        )
    
    return household


async def get_user_household_membership(
    household_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserHousehold:
    """Get user's household membership or raise 403."""
    membership = db.query(UserHousehold).filter(
        UserHousehold.household_id == household_id,
        UserHousehold.user_id == current_user.id,
        UserHousehold.is_active == True
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this household"
        )
    
    return membership


async def require_household_admin(
    household_id: UUID,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(lambda db=Depends(get_db): HouseholdService(db))
) -> UserHousehold:
    """Require user to be admin of the household."""
    has_permission = await household_service.check_user_permission(
        user_id=current_user.id,
        household_id=household_id,
        required_role="admin"
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this operation"
        )
    
    # Return the membership for further use
    membership = await get_user_household_membership(household_id, current_user)
    return membership


async def require_household_member(
    household_id: UUID,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(lambda db=Depends(get_db): HouseholdService(db))
) -> UserHousehold:
    """Require user to be a member of the household."""
    has_permission = await household_service.check_user_permission(
        user_id=current_user.id,
        household_id=household_id
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of this household"
        )
    
    # Return the membership for further use
    membership = await get_user_household_membership(household_id, current_user)
    return membership


def get_household_service(db: Session = Depends(get_db)) -> HouseholdService:
    """Get household service dependency."""
    return HouseholdService(db)


def get_expense_service(db: Session = Depends(get_db)):
    """Get expense service dependency."""
    from app.modules.expenses.services import ExpenseService
    return ExpenseService(db)


def get_splitting_service(db: Session = Depends(get_db)):
    """Get splitting service dependency."""
    from app.modules.expenses.services import SplittingService
    return SplittingService(db)


def get_analytics_service(db: Session = Depends(get_db)):
    """Get analytics service dependency."""
    from app.modules.expenses.services import AnalyticsService
    return AnalyticsService(db) 