"""
API endpoints for household management.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
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


# Member Management Endpoints
@router.post("/{household_id}/invite-member")
async def invite_member(
    household_id: UUID,
    email: str = Form(...),
    role: str = Form("member"),
    nickname: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Invite a new member to the household (admin only)."""
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
                detail="You don't have permission to invite members to this household"
            )
        
        # For now, simulate the invitation process
        # In a real implementation, this would:
        # 1. Check if user with email exists
        # 2. Send invitation email
        # 3. Create invitation record
        
        # For testing: Check if user exists and add them directly
        from app.modules.auth.models.user import User as AuthUser
        from app.modules.expenses.models.household import UserHousehold
        db = household_service.db
        
        # Check if user with this email exists
        existing_user = db.query(AuthUser).filter(AuthUser.email == email).first()
        
        if existing_user:
            # Check if they're already a member
            existing_membership = (
                db.query(UserHousehold)
                .filter(
                    UserHousehold.household_id == household_id,
                    UserHousehold.user_id == existing_user.id,
                    UserHousehold.is_active == True
                )
                .first()
            )
            
            if existing_membership:
                message = f"User {email} is already a member of this household."
                status_class = "yellow"
                icon_path = "M8.257 3.099c.765-1.36 2.722-1.36 3.478 0l5.58 9.92c.75 1.334-.213 2.98-1.739 2.98H4.424c-1.526 0-2.49-1.646-1.739-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
            else:
                # Add them as a member
                new_membership = UserHousehold(
                    household_id=household_id,
                    user_id=existing_user.id,
                    role=role,
                    nickname=nickname,
                    is_active=True
                )
                db.add(new_membership)
                db.commit()
                
                message = f"User {email} has been added to the household successfully!"
                status_class = "green"
                icon_path = "M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
        else:
            message = f"No user found with email {email}. In a real system, an invitation email would be sent."
            status_class = "blue"
            icon_path = "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
        
        # Simulate success response for testing
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=f"""
            <div class="p-4 bg-{status_class}-50 border border-{status_class}-200 rounded-md">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-{status_class}-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="{icon_path}" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-{status_class}-800">{'Success!' if status_class == 'green' else 'Notice'}</h3>
                        <div class="mt-2 text-sm text-{status_class}-700">
                            <p>{message}</p>
                        </div>
                    </div>
                </div>
            </div>
            <script>
                // Close the modal after 2 seconds
                setTimeout(() => {{
                    window.location.reload();
                }}, 2000);
            </script>
            """,
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inviting member: {e}")
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=f"""
            <div class="p-4 bg-red-50 border border-red-200 rounded-md">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">Error Sending Invitation</h3>
                        <div class="mt-2 text-sm text-red-700">
                            <p>Failed to send invitation. Please try again.</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
            status_code=500
        )


@router.put("/{household_id}/members/{user_id}")
async def update_member(
    household_id: UUID,
    user_id: UUID,
    nickname: Optional[str] = Form(None),
    role: str = Form("member"),
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Update a household member's role or nickname (admin only)."""
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
                detail="You don't have permission to update members in this household"
            )
        
        # Find the user household relationship
        from app.modules.expenses.models.household import UserHousehold
        db = household_service.db
        
        user_household = (
            db.query(UserHousehold)
            .filter(
                UserHousehold.household_id == household_id,
                UserHousehold.user_id == user_id,
                UserHousehold.is_active == True
            )
            .first()
        )
        
        if not user_household:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this household"
            )
        
        # Update the member
        if nickname is not None:
            user_household.nickname = nickname if nickname.strip() else None
        if role in ['member', 'admin']:
            user_household.role = role
        
        db.commit()
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=f"""
            <div class="p-4 bg-green-50 border border-green-200 rounded-md">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-green-800">Member Updated!</h3>
                        <div class="mt-2 text-sm text-green-700">
                            <p>Member information has been updated successfully.</p>
                        </div>
                    </div>
                </div>
            </div>
            <script>
                // Refresh the page after 1 second to show updates
                setTimeout(() => {{
                    window.location.reload();
                }}, 1000);
            </script>
            """,
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member: {e}")
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=f"""
            <div class="p-4 bg-red-50 border border-red-200 rounded-md">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">Error Updating Member</h3>
                        <div class="mt-2 text-sm text-red-700">
                            <p>Failed to update member. Please try again.</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
            status_code=500
        )


@router.delete("/{household_id}/members/{user_id}")
async def remove_member(
    household_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    household_service: HouseholdService = Depends(get_household_service)
):
    """Remove a member from the household (admin only)."""
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
                detail="You don't have permission to remove members from this household"
            )
        
        # Prevent removing yourself
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot remove yourself from the household"
            )
        
        # Find the user household relationship
        from app.modules.expenses.models.household import UserHousehold
        db = household_service.db
        
        user_household = (
            db.query(UserHousehold)
            .filter(
                UserHousehold.household_id == household_id,
                UserHousehold.user_id == user_id,
                UserHousehold.is_active == True
            )
            .first()
        )
        
        if not user_household:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this household"
            )
        
        # Soft delete the membership
        user_household.is_active = False
        db.commit()
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=f"""
            <div class="p-4 bg-green-50 border border-green-200 rounded-md">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-green-800">Member Removed!</h3>
                        <div class="mt-2 text-sm text-green-700">
                            <p>Member has been removed from the household successfully.</p>
                        </div>
                    </div>
                </div>
            </div>
            <script>
                // Refresh the page after 1 second to show updates
                setTimeout(() => {{
                    window.location.reload();
                }}, 1000);
            </script>
            """,
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing member: {e}")
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=f"""
            <div class="p-4 bg-red-50 border border-red-200 rounded-md">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">Error Removing Member</h3>
                        <div class="mt-2 text-sm text-red-700">
                            <p>Failed to remove member. Please try again.</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
            status_code=500
        ) 