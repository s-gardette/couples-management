"""
API endpoints for category management.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models.user import User
from app.modules.expenses.services import HouseholdService
from app.modules.expenses.models import Category
from app.modules.expenses.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryDetailResponse,
    CategoryListResponse,
    CategoryStatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["categories"])


def get_household_service(db: Session = Depends(get_db)) -> HouseholdService:
    """Get household service instance."""
    return HouseholdService(db)


@router.get("/households/{household_id}/categories", response_model=CategoryListResponse)
async def get_household_categories(
    household_id: UUID,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service),
    db: Session = Depends(get_db)
):
    """Get all categories available to a household (global + household-specific)."""
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
        
        # Get global categories
        global_categories = db.query(Category).filter(
            Category.household_id.is_(None),
            Category.is_active == True
        ).all()
        
        # Get household-specific categories
        household_categories = db.query(Category).filter(
            Category.household_id == household_id,
            Category.is_active == True
        ).all()
        
        # Convert to response format
        global_cat_responses = [
            CategoryDetailResponse(
                id=cat.id,
                name=cat.name,
                icon=cat.icon,
                color=cat.color,
                household_id=cat.household_id,
                is_default=cat.is_default,
                is_global=cat.is_global
            ) for cat in global_categories
        ]
        
        household_cat_responses = [
            CategoryDetailResponse(
                id=cat.id,
                name=cat.name,
                icon=cat.icon,
                color=cat.color,
                household_id=cat.household_id,
                is_default=cat.is_default,
                is_global=cat.is_global
            ) for cat in household_categories
        ]
        
        all_categories = global_cat_responses + household_cat_responses
        
        return CategoryListResponse(
            categories=all_categories,
            total=len(all_categories),
            global_categories=global_cat_responses,
            household_categories=household_cat_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting household categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve categories"
        )


@router.post("/households/{household_id}/categories", response_model=CategoryDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_household_category(
    household_id: UUID,
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service),
    db: Session = Depends(get_db)
):
    """Create a new household-specific category."""
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
        
        # Check if category name already exists in this household
        existing_category = db.query(Category).filter(
            Category.household_id == household_id,
            Category.name == category_data.name,
            Category.is_active == True
        ).first()
        
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A category with this name already exists in this household"
            )
        
        # Create new category
        new_category = Category.create_household_category(
            name=category_data.name,
            household_id=household_id,
            icon=category_data.icon,
            color=category_data.color,
            is_default=category_data.is_default
        )
        
        db.add(new_category)
        db.commit()
        db.refresh(new_category)
        
        return CategoryDetailResponse(
            id=new_category.id,
            name=new_category.name,
            icon=new_category.icon,
            color=new_category.color,
            household_id=new_category.household_id,
            is_default=new_category.is_default,
            is_global=new_category.is_global
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create category"
        )


@router.put("/categories/{category_id}", response_model=CategoryDetailResponse)
async def update_category(
    category_id: UUID,
    category_data: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service),
    db: Session = Depends(get_db)
):
    """Update a category (only household-specific categories can be updated)."""
    try:
        # Get the category
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.is_active == True
        ).first()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Check if it's a global category (cannot be updated)
        if category.is_global:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Global categories cannot be updated"
            )
        
        # Check if user has access to this household
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=category.household_id
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this household"
            )
        
        # Update category fields
        update_data = category_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)
        
        db.commit()
        db.refresh(category)
        
        return CategoryDetailResponse(
            id=category.id,
            name=category.name,
            icon=category.icon,
            color=category.color,
            household_id=category.household_id,
            is_default=category.is_default,
            is_global=category.is_global
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category"
        )


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service),
    db: Session = Depends(get_db)
):
    """Delete a category (only household-specific categories can be deleted)."""
    try:
        # Get the category
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.is_active == True
        ).first()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Check if it's a global category (cannot be deleted)
        if category.is_global:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Global categories cannot be deleted"
            )
        
        # Check if user has access to this household
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=category.household_id
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this household"
            )
        
        # Check if category is being used by any expenses
        from app.modules.expenses.models import Expense
        expenses_using_category = db.query(Expense).filter(
            Expense.category_id == category_id,
            Expense.is_active == True
        ).count()
        
        if expenses_using_category > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete category. It is being used by {expenses_using_category} expense(s)."
            )
        
        # Soft delete the category
        category.is_active = False
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category"
        )


@router.get("/households/{household_id}/categories/stats", response_model=List[CategoryStatsResponse])
async def get_category_statistics(
    household_id: UUID,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service),
    db: Session = Depends(get_db)
):
    """Get category usage statistics for a household."""
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
        
        # Get category statistics using raw SQL for better performance
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                c.id as category_id,
                c.name as category_name,
                c.color,
                c.icon,
                COUNT(e.id) as expense_count,
                COALESCE(SUM(e.amount), 0) as total_amount,
                COALESCE(AVG(e.amount), 0) as average_amount
            FROM categories c
            LEFT JOIN expenses e ON c.id = e.category_id 
                AND e.household_id = :household_id 
                AND e.is_active = true
            WHERE (c.household_id = :household_id OR c.household_id IS NULL)
                AND c.is_active = true
            GROUP BY c.id, c.name, c.color, c.icon
            ORDER BY total_amount DESC
        """)
        
        result = db.execute(query, {"household_id": str(household_id)}).fetchall()
        
        # Calculate total amount for percentage calculation
        total_household_amount = sum(row.total_amount for row in result)
        
        # Convert to response format
        stats = []
        for row in result:
            percentage = (float(row.total_amount) / float(total_household_amount) * 100) if total_household_amount > 0 else 0
            
            stats.append(CategoryStatsResponse(
                category_id=row.category_id,
                category_name=row.category_name,
                expense_count=row.expense_count,
                total_amount=float(row.total_amount),
                average_amount=float(row.average_amount),
                percentage_of_total=percentage,
                color=row.color,
                icon=row.icon
            ))
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category statistics"
        ) 