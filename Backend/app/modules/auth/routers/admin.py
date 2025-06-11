"""
Admin-only user management API endpoints.
"""

from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_admin_user
from app.modules.auth.models.user import User, UserRole
from app.modules.auth.schemas.user import UserResponse, UserCreate, UserUpdate
from app.modules.auth.schemas.admin import (
    AdminUserCreateRequest,
    AdminUserCreateResponse,
    AdminUserListResponse,
    AdminUserStatsResponse,
    AdminUserInviteRequest,
    AdminUserInviteResponse,
    AdminBulkUserImportRequest,
    AdminBulkUserImportResponse
)
from app.modules.auth.services.user_service import UserService
from app.modules.auth.services.auth_service import AuthService

router = APIRouter(prefix="/admin", tags=["Admin User Management"])


@router.post("/users", response_model=AdminUserCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
    user_data: AdminUserCreateRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user account (admin only).
    
    Only admin users can create new user accounts.
    """
    user_service = UserService(db)
    auth_service = AuthService(db)
    
    # Check if email or username already exists
    existing_user = await user_service.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_user = await user_service.get_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user with admin tracking
    success, message, user = await auth_service.register_user(
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        created_by_admin=True,
        admin_id=str(current_admin.id)
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Set role if specified
    if user_data.role:
        user.role = UserRole(user_data.role)
    
    # Set admin-specific fields
    user.set_created_by_admin(str(current_admin.id))
    if user_data.require_password_change:
        user.require_password_change()
    
    # Auto-verify email for admin-created users
    user.verify_email()
    user.activate()
    
    db.commit()
    
    return AdminUserCreateResponse(
        message="User created successfully",
        user_id=str(user.id),
        temporary_password=user_data.password if user_data.send_temporary_password else None,
        invitation_sent=user_data.send_invitation_email
    )


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None)
):
    """
    List all users with filtering and pagination (admin only).
    """
    user_service = UserService(db)
    
    # Build filters
    filters = {}
    if role:
        filters['role'] = UserRole(role)
    if is_active is not None:
        filters['is_active'] = is_active
    
    users, total = await user_service.list_users_with_filters(
        skip=skip,
        limit=limit,
        search=search,
        **filters
    )
    
    return AdminUserListResponse(
        users=[UserResponse.model_validate(user) for user in users],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_admin(
    user_id: UUID,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get user details by ID (admin only).
    """
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_by_admin(
    user_id: UUID,
    user_data: UserUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update user by ID (admin only).
    """
    user_service = UserService(db)
    user = await user_service.update(user_id, user_data)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}/activate")
async def activate_user(
    user_id: UUID,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Activate user account (admin only).
    """
    user_service = UserService(db)
    success = await user_service.activate_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User activated successfully"}


@router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Deactivate user account (admin only).
    """
    user_service = UserService(db)
    success = await user_service.deactivate_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deactivated successfully"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account (admin only).
    """
    # Prevent admin from deleting themselves
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user_service = UserService(db)
    success = await user_service.delete(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deleted successfully"}


@router.post("/users/invite", response_model=AdminUserInviteResponse)
async def invite_user(
    invite_data: AdminUserInviteRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Send user invitation email (admin only).
    """
    # TODO: Implement email invitation system
    # For now, return a placeholder response
    
    return AdminUserInviteResponse(
        message="User invitation sent successfully",
        invitation_token="placeholder-token",
        expires_at="2025-06-01T00:00:00Z"
    )


@router.post("/users/bulk-import", response_model=AdminBulkUserImportResponse)
async def bulk_import_users(
    import_data: AdminBulkUserImportRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Bulk import users from CSV/JSON data (admin only).
    """
    # TODO: Implement bulk user import
    # For now, return a placeholder response
    
    return AdminBulkUserImportResponse(
        message="Bulk import completed",
        imported_count=0,
        failed_count=0,
        errors=[]
    )


@router.get("/stats", response_model=AdminUserStatsResponse)
async def get_user_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get user statistics (admin only).
    """
    user_service = UserService(db)
    stats = await user_service.get_user_statistics()
    
    return AdminUserStatsResponse(**stats) 