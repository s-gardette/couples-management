"""
User management API endpoints.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import (
    get_current_active_user,
    get_current_admin_user,
    get_current_user,
    get_current_verified_user,
    get_current_user_optional,
)
from app.modules.auth.models.user import User
from app.modules.auth.schemas.auth import AuthResponse
from app.modules.auth.schemas.user import (
    AvailabilityResponse,
    AvatarUpdate,
    EmailAvailability,
    PasswordChange,
    UsernameAvailability,
    UserProfile,
    UserResponse,
    UserStats,
    UserUpdate,
    UserListResponse,
    UserCreate,
)
from app.modules.auth.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User Management"])


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Get user service instance."""
    return UserService(db)


@router.get("/me", response_model=UserProfile)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile information.

    Returns detailed profile information for the authenticated user.
    """
    return UserProfile.model_validate(current_user)


@router.put("/me", response_model=UserProfile)
async def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile information.

    Allows users to update their profile details like name, email, and username.
    """
    user_service = UserService(db)

    success, message, updated_user = await user_service.update_user_profile(
        user_id=current_user.id,
        first_name=user_update.first_name,
        last_name=user_update.last_name,
        email=user_update.email,
        username=user_update.username
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return UserProfile.model_validate(updated_user)


@router.put("/me/password", response_model=AuthResponse)
async def change_my_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password.

    Validates current password and updates to new password with security checks.
    """
    user_service = UserService(db)

    success, message = await user_service.change_password(
        user_id=current_user.id,
        current_password=password_change.current_password,
        new_password=password_change.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return AuthResponse(
        success=True,
        message=message
    )


@router.put("/me/avatar", response_model=AuthResponse)
async def update_my_avatar(
    avatar_update: AvatarUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's avatar.

    Updates the user's avatar URL.
    """
    user_service = UserService(db)

    success, message = await user_service.update_avatar(
        user_id=current_user.id,
        avatar_url=avatar_update.avatar_url
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return AuthResponse(
        success=True,
        message=message
    )


@router.get("/search", response_model=list[UserResponse])
async def search_users(
    query: str = Query(None, description="Search query"),
    email_verified: bool = Query(None, description="Filter by email verification"),
    is_active: bool = Query(None, description="Filter by active status"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Search and filter users.

    Allows verified users to search for other users with various filters.
    """
    user_service = UserService(db)

    users = await user_service.search_users(
        query=query,
        email_verified=email_verified,
        is_active=is_active,
        limit=limit,
        offset=offset
    )

    return [UserResponse.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Get user by ID.

    Returns public profile information for a specific user.
    """
    user_service = UserService(db)

    user = await user_service.get_user_profile(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.model_validate(user)


@router.post("/check-email", response_model=AvailabilityResponse)
async def check_email_availability(
    email_check: EmailAvailability,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Check if email address is available.

    Validates if an email address is available for use.
    Public endpoint for registration, but can exclude current user if authenticated.
    """
    user_service = UserService(db)

    is_available = await user_service.check_email_availability(
        email=email_check.email,
        exclude_user_id=current_user.id if current_user else None
    )

    return AvailabilityResponse(
        available=is_available,
        message="Email is available" if is_available else "Email is already in use"
    )


@router.post("/check-username", response_model=AvailabilityResponse)
async def check_username_availability(
    username_check: UsernameAvailability,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Check if username is available.

    Validates if a username is available for use.
    Public endpoint for registration, but can exclude current user if authenticated.
    """
    user_service = UserService(db)

    is_available = await user_service.check_username_availability(
        username=username_check.username,
        exclude_user_id=current_user.id if current_user else None
    )

    return AvailabilityResponse(
        available=is_available,
        message="Username is available" if is_available else "Username is already taken"
    )


# Admin endpoints
@router.get("/admin/stats", response_model=UserStats)
async def get_user_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get user statistics (Admin only).

    Returns comprehensive user statistics for administrators.
    """
    user_service = UserService(db)

    stats = await user_service.get_user_stats()
    return UserStats(**stats)


@router.get("/admin/recent", response_model=list[UserResponse])
async def get_recent_users(
    limit: int = Query(10, ge=1, le=50, description="Number of recent users"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get recently registered users (Admin only).

    Returns a list of recently registered users for administrators.
    """
    user_service = UserService(db)

    users = await user_service.get_recent_users(limit=limit)
    return [UserResponse.model_validate(user) for user in users]


@router.put("/admin/{user_id}/activate", response_model=AuthResponse)
async def activate_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Activate a user account (Admin only).

    Activates a deactivated user account.
    """
    user_service = UserService(db)

    success, message = await user_service.activate_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return AuthResponse(
        success=True,
        message=message
    )


@router.put("/admin/{user_id}/deactivate", response_model=AuthResponse)
async def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Deactivate a user account (Admin only).

    Deactivates a user account, preventing login.
    """
    user_service = UserService(db)

    success, message = await user_service.deactivate_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return AuthResponse(
        success=True,
        message=message
    )


@router.delete("/admin/{user_id}", response_model=AuthResponse)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete a user account (Admin only).

    Soft deletes a user account and all associated data.
    """
    user_service = UserService(db)

    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    success, message = await user_service.delete_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return AuthResponse(
        success=True,
        message=message
    )


@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by email or username"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(get_user_service)
):
    """List all users (admin only)."""
    try:
        # Build filters
        filters = {}
        if search:
            filters['search'] = search
        if role:
            filters['role'] = role
        if is_active is not None:
            filters['is_active'] = is_active
        
        # Calculate skip for pagination
        skip = (page - 1) * per_page
        
        success, message, users = await user_service.list_users(
            skip=skip,
            limit=per_page,
            filters=filters
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Get total count (simplified approach)
        total = len(users)  # This would need proper total count implementation
        
        return UserListResponse(
            users=users,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(get_user_service)
):
    """Get user by ID (admin only)."""
    try:
        user = await user_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(get_user_service)
):
    """Create a new user (admin only)."""
    try:
        success, message, new_user = await user_service.create_user(
            user_data=user_data,
            created_by_admin_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return new_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(get_user_service)
):
    """Update user (admin only)."""
    try:
        success, message, updated_user = await user_service.update_user(
            user_id=user_id,
            user_data=user_data.model_dump(exclude_unset=True)
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(get_user_service)
):
    """Delete user (admin only)."""
    try:
        # Prevent deleting yourself
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot delete your own account"
            )
        
        success, message = await user_service.delete_user(user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )
