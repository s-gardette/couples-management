"""
API endpoints for household management.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models.user import User
from app.modules.expenses.services import HouseholdService
from app.modules.expenses.schemas import (
    HouseholdCreate,
    HouseholdUpdate,
    HouseholdResponse,
    HouseholdListResponse,
    JoinHouseholdRequest,
    UpdateMemberRoleRequest,
    HouseholdSettingsUpdate,
    InviteCodeResponse,
    HouseholdStatsResponse,
    HouseholdMembersResponse,
    HouseholdMemberResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/households", tags=["households"])


def get_household_service(db: Session = Depends(get_db)) -> HouseholdService:
    """Get household service instance."""
    return HouseholdService(db)


@router.post("/", response_model=HouseholdResponse, status_code=status.HTTP_201_CREATED)
async def create_household(
    household_data: HouseholdCreate,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Create a new household."""
    try:
        success, message, household = await household_service.create_household(
            name=household_data.name,
            description=household_data.description,
            created_by=current_user.id,
            settings=household_data.settings
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return household
        
    except Exception as e:
        logger.error(f"Error creating household: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create household"
        )


@router.get("/", response_model=List[HouseholdResponse])
async def get_user_households(
    include_inactive: bool = Query(False, description="Include inactive households"),
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Get all households for the current user."""
    try:
        households = await household_service.get_user_households(
            user_id=current_user.id,
            include_inactive=include_inactive
        )
        return households
        
    except Exception as e:
        logger.error(f"Error getting user households: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve households"
        )


@router.get("/{household_id}", response_model=HouseholdResponse)
async def get_household_details(
    household_id: UUID,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Get household details with member information."""
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
        
        household = await household_service.get_household_with_members(household_id)
        
        if not household:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Household not found"
            )
        
        return household
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting household details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve household details"
        )


@router.put("/{household_id}", response_model=HouseholdResponse)
async def update_household(
    household_id: UUID,
    household_data: HouseholdUpdate,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Update household information (admin only)."""
    try:
        # Check if user is admin of this household
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=household_id,
            required_role="admin"
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this household"
            )
        
        # Get current household
        household = await household_service.get_household_with_members(household_id)
        if not household:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Household not found"
            )
        
        # Update household fields
        update_data = household_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(household, field, value)
        
        household_service.db.commit()
        return household
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating household: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update household"
        )


@router.delete("/{household_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_household(
    household_id: UUID,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Delete household (admin only)."""
    try:
        # Check if user is admin of this household
        has_permission = await household_service.check_user_permission(
            user_id=current_user.id,
            household_id=household_id,
            required_role="admin"
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this household"
            )
        
        # Soft delete the household
        household = household_service.get(household_service.db, household_id)
        if not household:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Household not found"
            )
        
        household.is_active = False
        household_service.db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting household: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete household"
        )


@router.post("/{household_id}/join", response_model=HouseholdResponse)
async def join_household_by_invite(
    household_id: UUID,
    join_data: JoinHouseholdRequest,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Join a household using an invite code."""
    try:
        success, message, household = await household_service.join_household_by_invite(
            user_id=current_user.id,
            invite_code=join_data.invite_code,
            nickname=join_data.nickname
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return household
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining household: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join household"
        )


@router.post("/{household_id}/invite", response_model=InviteCodeResponse)
async def regenerate_invite_code(
    household_id: UUID,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Regenerate household invite code (admin only)."""
    try:
        success, message, new_invite_code = await household_service.regenerate_invite_code(
            user_id=current_user.id,
            household_id=household_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=message
            )
        
        household = await household_service.get_household_with_members(household_id)
        
        return InviteCodeResponse(
            invite_code=new_invite_code,
            household_id=household_id,
            household_name=household.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating invite code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate invite code"
        )


@router.get("/{household_id}/members", response_model=HouseholdMembersResponse)
async def get_household_members(
    household_id: UUID,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Get household members list."""
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
        
        household = await household_service.get_household_with_members(household_id)
        if not household:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Household not found"
            )
        
        # Convert members to response format
        members = []
        for member in household.members:
            if member.is_active:
                members.append(HouseholdMemberResponse(
                    user_id=member.user_id,
                    username=member.user.username,
                    email=member.user.email,
                    role=member.role,
                    nickname=member.nickname,
                    joined_at=member.joined_at,
                    is_active=member.is_active
                ))
        
        return HouseholdMembersResponse(
            members=members,
            total=len(members),
            household_id=household_id,
            household_name=household.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting household members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve household members"
        )


@router.put("/{household_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def update_member_role(
    household_id: UUID,
    user_id: UUID,
    role_data: UpdateMemberRoleRequest,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Update member role (admin only)."""
    try:
        success, message = await household_service.update_member_role(
            admin_user_id=current_user.id,
            household_id=household_id,
            target_user_id=user_id,
            new_role=role_data.role
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=message
            )
        
        return {"message": message}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update member role"
        )


@router.delete("/{household_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    household_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Remove member from household (admin only)."""
    try:
        success, message = await household_service.remove_member(
            admin_user_id=current_user.id,
            household_id=household_id,
            target_user_id=user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=message
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member"
        )


@router.post("/{household_id}/leave", status_code=status.HTTP_200_OK)
async def leave_household(
    household_id: UUID,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Leave a household."""
    try:
        success, message = await household_service.leave_household(
            user_id=current_user.id,
            household_id=household_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return {"message": message}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error leaving household: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to leave household"
        )


@router.put("/{household_id}/settings", response_model=HouseholdResponse)
async def update_household_settings(
    household_id: UUID,
    settings_data: HouseholdSettingsUpdate,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Update household settings (admin only)."""
    try:
        success, message, household = await household_service.update_household_settings(
            user_id=current_user.id,
            household_id=household_id,
            settings=settings_data.settings
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=message
            )
        
        return household
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating household settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update household settings"
        )


@router.get("/{household_id}/stats", response_model=HouseholdStatsResponse)
async def get_household_stats(
    household_id: UUID,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Get household statistics."""
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
        
        stats = await household_service.get_household_stats(household_id)
        
        return HouseholdStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting household stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve household statistics"
        ) 