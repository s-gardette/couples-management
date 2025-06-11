"""
Admin UI dependencies for authentication and authorization.
"""

import logging
from typing import Optional, Set
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user_from_cookie_or_header
from app.modules.auth.models.user import User
from app.config import settings

logger = logging.getLogger(__name__)

# Define explicit admin permissions - DENY BY DEFAULT
ADMIN_PERMISSIONS = {
    'users.view': 'View user list and details',
    'users.create': 'Create new users',
    'users.edit': 'Edit user information',
    'users.delete': 'Delete users',
    'users.password': 'Change user passwords',
    'system.settings': 'Access system settings',
    'system.logs': 'View system logs',
    'admin.manage': 'Manage other admins'
}

# Default permission set for new admins - START RESTRICTIVE
DEFAULT_ADMIN_PERMISSIONS = {
    'users.view'  # Only view users by default
}

def get_user_admin_permissions(user: User) -> Set[str]:
    """
    Get the set of admin permissions for a user.
    DEFAULTS TO EMPTY SET - NO PERMISSIONS.
    
    Args:
        user: The user to get permissions for
        
    Returns:
        Set[str]: Set of permission strings the user has
    """
    if not user or not user.is_admin() or not user.is_active:
        return set()  # NO PERMISSIONS BY DEFAULT
    
    # TODO: Implement database-backed permission storage
    # For now, use a simple mapping based on user properties
    # CRITICAL: This should be moved to database with explicit grants
    
    # Super restrictive: only give default permissions
    # Admin users should be granted specific permissions explicitly
    user_permissions = DEFAULT_ADMIN_PERMISSIONS.copy()
    
    # Temporary escalation for existing admin workflow
    # TODO: Remove this and implement proper permission assignment UI
    if user.email == 'admin@gmail.com':  # Only the main admin gets full access
        user_permissions = set(ADMIN_PERMISSIONS.keys())
    
    logger.info(f"User {user.email} has permissions: {user_permissions}")
    return user_permissions


async def get_current_admin_user(
    current_user: User = Depends(get_current_user_from_cookie_or_header),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current user and verify they have admin privileges.
    ZERO-TRUST: Verify every aspect before granting access.
    
    Args:
        current_user: The currently authenticated user
        db: Database session
        
    Returns:
        User: The authenticated admin user
        
    Raises:
        HTTPException: If user is not authenticated or not an admin
    """
    # EXPLICIT CHECKS - DENY BY DEFAULT
    
    if current_user is None:
        logger.warning("Admin access attempted without authentication")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Verify user object integrity
    if not hasattr(current_user, 'is_admin') or not callable(current_user.is_admin):
        logger.error(f"User object integrity check failed for {getattr(current_user, 'email', 'unknown')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if user has admin role - EXPLICIT CALL
    if not current_user.is_admin():
        logger.warning(f"Non-admin user {current_user.email} attempted admin access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    # Verify user account is active
    if not current_user.is_active:
        logger.warning(f"Inactive admin user {current_user.email} attempted access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Additional security checks
    if not current_user.email or '@' not in current_user.email:
        logger.error(f"Admin user has invalid email: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user account"
        )
    
    logger.info(f"Admin access granted to {current_user.email}")
    return current_user


async def require_admin_auth(
    admin_user: User = Depends(get_current_admin_user)
) -> User:
    """
    Dependency that requires admin authentication.
    
    This is a convenience wrapper around get_current_admin_user
    for use in route dependencies.
    
    Args:
        admin_user: The authenticated admin user
        
    Returns:
        User: The authenticated admin user
    """
    return admin_user


def check_admin_permission(user: User, permission: str) -> bool:
    """
    Check if admin user has specific permission.
    ZERO-TRUST: DENY BY DEFAULT, require explicit permission grant.
    
    Args:
        user: The user to check permissions for
        permission: The permission to check (e.g., 'users.create', 'system.settings')
        
    Returns:
        bool: True if user has permission, False otherwise
    """
    # DENY BY DEFAULT
    if not user:
        logger.warning(f"Permission check failed: no user provided for permission '{permission}'")
        return False
    
    if not user.is_admin():
        logger.warning(f"Permission check failed: user {user.email} is not admin for permission '{permission}'")
        return False
    
    if not user.is_active:
        logger.warning(f"Permission check failed: user {user.email} is inactive for permission '{permission}'")
        return False
    
    # Check if permission exists in our defined set
    if permission not in ADMIN_PERMISSIONS:
        logger.error(f"Unknown permission requested: {permission}")
        return False
    
    # Get user's actual permissions
    user_permissions = get_user_admin_permissions(user)
    has_permission = permission in user_permissions
    
    if not has_permission:
        logger.warning(f"Admin user {user.email} lacks permission: {permission}")
    
    return has_permission


async def require_admin_permission(
    permission: str,
    admin_user: User = Depends(get_current_admin_user)
) -> User:
    """
    Dependency that requires specific admin permission.
    ZERO-TRUST: Explicit permission required, no broad access.
    
    Args:
        permission: The required permission
        admin_user: The authenticated admin user
        
    Returns:
        User: The authenticated admin user
        
    Raises:
        HTTPException: If user doesn't have the required permission
    """
    if not check_admin_permission(admin_user, permission):
        logger.warning(f"Admin user {admin_user.email} denied access for permission: {permission}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission required: {permission}"
        )
    
    return admin_user 