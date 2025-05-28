"""
Auth module security utilities.
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from uuid import UUID

from app.core.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    generate_random_string
)
from app.config import settings


def generate_verification_token() -> str:
    """
    Generate a secure email verification token.
    
    Returns:
        Secure random token for email verification
    """
    return secrets.token_urlsafe(32)


def generate_password_reset_token_secure() -> str:
    """
    Generate a secure password reset token.
    
    Returns:
        Secure random token for password reset
    """
    return secrets.token_urlsafe(32)


def generate_session_token() -> str:
    """
    Generate a secure session token.
    
    Returns:
        Secure random token for session management
    """
    return secrets.token_urlsafe(64)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with auth module context.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return get_password_hash(password)


def verify_password_secure(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password with additional security checks.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches and passes security checks
    """
    # Basic password verification
    if not verify_password(plain_password, hashed_password):
        return False
    
    # Additional security checks could be added here
    # For example: check if password needs rehashing due to updated security settings
    
    return True


def create_user_tokens(user_id: UUID) -> Dict[str, str]:
    """
    Create access and refresh tokens for a user.
    
    Args:
        user_id: User UUID
        
    Returns:
        Dictionary containing access_token and refresh_token
    """
    access_token = create_access_token(subject=str(user_id))
    refresh_token = create_refresh_token(subject=str(user_id))
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def generate_secure_random_password(length: int = 12) -> str:
    """
    Generate a secure random password.
    
    Args:
        length: Length of the password (minimum 8)
        
    Returns:
        Secure random password
    """
    if length < 8:
        length = 8
    
    # Ensure password contains all required character types
    password_chars = []
    
    # Add required characters
    if settings.auth_password_require_uppercase:
        password_chars.append(secrets.choice(string.ascii_uppercase))
    if settings.auth_password_require_lowercase:
        password_chars.append(secrets.choice(string.ascii_lowercase))
    if settings.auth_password_require_numbers:
        password_chars.append(secrets.choice(string.digits))
    if settings.auth_password_require_special:
        password_chars.append(secrets.choice("!@#$%^&*(),.?\":{}|<>"))
    
    # Fill remaining length with random characters
    all_chars = string.ascii_letters + string.digits + "!@#$%^&*(),.?\":{}|<>"
    remaining_length = length - len(password_chars)
    
    for _ in range(remaining_length):
        password_chars.append(secrets.choice(all_chars))
    
    # Shuffle the password characters
    secrets.SystemRandom().shuffle(password_chars)
    
    return ''.join(password_chars)


def is_token_expired(expires_at: datetime) -> bool:
    """
    Check if a token has expired.
    
    Args:
        expires_at: Token expiration datetime
        
    Returns:
        True if token has expired
    """
    return datetime.utcnow() > expires_at


def get_token_expiry_time(hours: int) -> datetime:
    """
    Get token expiry time from now.
    
    Args:
        hours: Hours from now
        
    Returns:
        Expiry datetime
    """
    return datetime.utcnow() + timedelta(hours=hours)


def mask_email(email: str) -> str:
    """
    Mask an email address for security/privacy.
    
    Args:
        email: Email address to mask
        
    Returns:
        Masked email address
    """
    if '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    
    if len(local) <= 2:
        masked_local = local[0] + '*'
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


def generate_device_fingerprint(user_agent: Optional[str], ip_address: Optional[str]) -> str:
    """
    Generate a device fingerprint for session tracking.
    
    Args:
        user_agent: User agent string
        ip_address: IP address
        
    Returns:
        Device fingerprint hash
    """
    import hashlib
    
    fingerprint_data = f"{user_agent or 'unknown'}:{ip_address or 'unknown'}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16] 