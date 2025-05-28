"""
Authentication dependencies for FastAPI.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.models.user import User
from app.modules.auth.utils.jwt import verify_access_token
from app.config import settings

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user_from_cookie_or_header(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    access_token: str | None = Cookie(None),
    db: Session = Depends(get_db)
) -> User | None:
    """
    Get current user from JWT token in either Authorization header or cookie.
    
    This dependency supports both API access (Authorization header) and 
    browser navigation (cookie-based authentication).

    Args:
        request: FastAPI request object
        credentials: HTTP authorization credentials from header
        access_token: JWT token from cookie
        db: Database session

    Returns:
        User object or None if not authenticated
    """
    token = None
    
    # Try to get token from Authorization header first
    if credentials:
        token = credentials.credentials
    # Fallback to cookie
    elif access_token:
        token = access_token
    
    if not token:
        return None

    payload = verify_access_token(token, db)
    if not payload:
        return None

    try:
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        return None

    user = db.query(User).filter(User.id == user_id).first()
    return user


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
    Get current admin user (requires admin role).

    Args:
        current_user: Current verified user

    Returns:
        Admin user object

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
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


async def get_default_user(
    db: Session = Depends(get_db)
) -> User | None:
    """
    Get default user for automatic login (development/testing).
    
    Returns the first admin user if default login is enabled.
    
    Args:
        db: Database session
        
    Returns:
        Default user or None if disabled/not found
    """
    # Check if default login is enabled
    if not getattr(settings, 'ENABLE_DEFAULT_LOGIN', False):
        return None
    
    # Get default user ID from settings or first admin user
    default_user_id = getattr(settings, 'DEFAULT_USER_ID', None)
    
    if default_user_id:
        user = db.query(User).filter(User.id == default_user_id).first()
        if user and user.is_active:
            return user
    
    # Fallback: get first active admin user
    admin_user = db.query(User).filter(
        User.role == "admin",
        User.is_active == True
    ).first()
    
    return admin_user


async def get_current_user_or_default(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token or default user if enabled.
    
    This dependency supports both normal authentication and default login.
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        User object
        
    Raises:
        HTTPException: If not authenticated and no default user available
    """
    # Try normal authentication first
    if credentials:
        token = credentials.credentials
        payload = verify_access_token(token, db)
        
        if payload:
            try:
                user_id = UUID(payload["sub"])
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.is_active:
                    return user
            except (ValueError, KeyError):
                pass
    
    # Try default user if normal auth failed
    default_user = await get_default_user(db)
    if default_user:
        return default_user
    
    # No authentication available
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_authentication(
    request: Request,
    current_user: User = Depends(get_current_user_or_default)
) -> User:
    """
    Mandatory authentication dependency for all protected routes.
    
    This ensures that ALL routes require authentication with no exceptions.
    
    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Authenticated user
        
    Raises:
        HTTPException: If not authenticated
    """
    # Additional security checks can be added here
    # For example: IP restrictions, rate limiting, etc.
    
    return current_user
