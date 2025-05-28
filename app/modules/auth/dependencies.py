"""
Authentication dependencies for FastAPI.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.models.user import User
from app.modules.auth.utils.jwt import verify_access_token

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db)
) -> User | None:
    """
    Get current user from JWT token (optional - returns None if no token or invalid).

    Args:
        credentials: HTTP authorization credentials
        db: Database session

    Returns:
        User object or None if not authenticated
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_access_token(token, db)

    if not payload:
        return None

    try:
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        return None

    user = db.query(User).filter(User.id == user_id).first()
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token (required - raises exception if not authenticated).

    Args:
        credentials: HTTP authorization credentials
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If not authenticated or user not found
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_access_token(token, db)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (must be authenticated and active).

    Args:
        current_user: Current user from get_current_user

    Returns:
        Active user object

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current verified user (must be authenticated, active, and email verified).

    Args:
        current_user: Current active user

    Returns:
        Verified user object

    Raises:
        HTTPException: If user email is not verified
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified"
        )

    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_verified_user)
) -> User:
    """
    Get current admin user (placeholder for future role-based access).

    Args:
        current_user: Current verified user

    Returns:
        Admin user object

    Raises:
        HTTPException: If user is not an admin
    """
    # TODO: Implement role-based access control
    # For now, we'll use a simple check (this should be replaced with proper RBAC)

    # Placeholder: Check if user email contains 'admin' (temporary)
    if "admin" not in current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    return current_user


def require_permissions(*permissions: str):
    """
    Dependency factory for permission-based access control (future implementation).

    Args:
        *permissions: Required permissions

    Returns:
        Dependency function
    """
    async def permission_checker(
        current_user: User = Depends(get_current_verified_user)
    ) -> User:
        # TODO: Implement permission checking
        # This is a placeholder for future role-based access control

        # For now, just return the user
        return current_user

    return permission_checker


def require_roles(*roles: str):
    """
    Dependency factory for role-based access control (future implementation).

    Args:
        *roles: Required roles

    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: User = Depends(get_current_verified_user)
    ) -> User:
        # TODO: Implement role checking
        # This is a placeholder for future role-based access control

        # For now, just return the user
        return current_user

    return role_checker


# Convenience dependencies for common use cases
CurrentUser = Depends(get_current_user)
CurrentActiveUser = Depends(get_current_active_user)
CurrentVerifiedUser = Depends(get_current_verified_user)
CurrentAdminUser = Depends(get_current_admin_user)
OptionalUser = Depends(get_current_user_optional)
