"""
Startup utilities for auth module.
"""

import logging
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.modules.auth.models.user import User, UserRole
from app.modules.auth.models.password_history import PasswordHistory
from app.core.utils.security import get_password_hash
from datetime import datetime

logger = logging.getLogger(__name__)


async def create_default_admin_user(db: Session) -> User | None:
    """
    Create default admin user if it doesn't exist.
    
    Args:
        db: Database session
        
    Returns:
        Created or existing admin user, or None if creation disabled
    """
    if not settings.create_default_admin:
        logger.info("Default admin creation is disabled")
        return None
    
    # Check if admin user already exists
    existing_admin = db.query(User).filter(
        User.email == settings.default_admin_email
    ).first()
    
    if existing_admin:
        logger.info(f"Default admin user already exists: {existing_admin.email}")
        # Ensure the user is an admin
        if not existing_admin.is_admin():
            existing_admin.make_admin()
            existing_admin.activate()
            existing_admin.verify_email()
            db.commit()
            logger.info(f"Promoted existing user to admin: {existing_admin.email}")
        return existing_admin
    
    # Create new admin user directly (bypass email validation)
    try:
        # Hash password
        hashed_password = get_password_hash(settings.default_admin_password)
        
        # Create user directly
        admin_user = User(
            email=settings.default_admin_email.lower(),
            username=settings.default_admin_username.lower(),
            hashed_password=hashed_password,
            first_name="System",
            last_name="Administrator",
            email_verified=True,  # Auto-verify admin email
            is_active=True,
            role=UserRole.ADMIN  # Use the enum directly
        )
        
        db.add(admin_user)
        db.flush()  # Get the user ID
        
        # Create password history entry
        password_history = PasswordHistory(
            user_id=admin_user.id,
            password_hash=hashed_password,
            changed_at=datetime.utcnow()
        )
        db.add(password_history)
        
        db.commit()
        
        logger.info(f"Created default admin user: {admin_user.email}")
        return admin_user
        
    except Exception as e:
        logger.error(f"Error creating default admin user: {e}")
        db.rollback()
        return None


async def initialize_auth_system(db: Session) -> dict:
    """
    Initialize the authentication system.
    
    Args:
        db: Database session
        
    Returns:
        Initialization results
    """
    results = {
        "admin_created": False,
        "admin_user": None,
        "default_login_enabled": settings.enable_default_login,
        "auth_required_for_all": settings.require_authentication_for_all
    }
    
    # Create default admin user
    admin_user = await create_default_admin_user(db)
    if admin_user:
        results["admin_created"] = True
        results["admin_user"] = admin_user
    
    # Log system configuration
    logger.info("Auth system initialization complete:")
    logger.info(f"  - Default login enabled: {settings.enable_default_login}")
    logger.info(f"  - Auth required for all routes: {settings.require_authentication_for_all}")
    logger.info(f"  - Default admin created: {results['admin_created']}")
    
    return results


def get_system_status() -> dict:
    """
    Get current auth system status.
    
    Returns:
        System status information
    """
    return {
        "default_login_enabled": settings.enable_default_login,
        "auth_required_for_all": settings.require_authentication_for_all,
        "admin_contact_email": settings.admin_contact_email,
        "admin_contact_message": settings.admin_contact_message,
        "create_default_admin": settings.create_default_admin
    } 