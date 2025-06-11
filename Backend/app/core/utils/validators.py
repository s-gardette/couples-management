"""
Validation utilities for common validation tasks.
"""

import re
from typing import Any

from email_validator import EmailNotValidError, validate_email

from app.config import settings


def validate_email_address(email: str) -> bool:
    """
    Validate an email address.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password strength based on configuration.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check minimum length
    if len(password) < settings.auth_password_min_length:
        errors.append(f"Password must be at least {settings.auth_password_min_length} characters long")

    # Check for uppercase letter
    if settings.auth_password_require_uppercase and not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")

    # Check for lowercase letter
    if settings.auth_password_require_lowercase and not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")

    # Check for numbers
    if settings.auth_password_require_numbers and not re.search(r'\d', password):
        errors.append("Password must contain at least one number")

    # Check for special characters
    if settings.auth_password_require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>\-_=\[\]\\\/~`+]', password):
        errors.append("Password must contain at least one special character")

    return len(errors) == 0, errors


def validate_username(username: str) -> tuple[bool, str | None]:
    """
    Validate username format.

    Args:
        username: Username to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"

    if len(username) < 3:
        return False, "Username must be at least 3 characters long"

    if len(username) > 50:
        return False, "Username must be less than 50 characters long"

    # Allow letters, numbers, underscores, and hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"

    return True, None


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        True if valid, False otherwise
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)

    # Check if it's a valid length (10-15 digits)
    return 10 <= len(digits_only) <= 15


def validate_currency_amount(amount: Any) -> tuple[bool, str | None]:
    """
    Validate currency amount.

    Args:
        amount: Amount to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        amount_float = float(amount)
    except (ValueError, TypeError):
        return False, "Amount must be a valid number"

    if amount_float < 0:
        return False, "Amount cannot be negative"

    if amount_float > settings.expenses_max_amount:
        return False, f"Amount cannot exceed {settings.expenses_max_amount}"

    # Check for reasonable decimal places (max 2)
    if round(amount_float, 2) != amount_float:
        return False, "Amount can have at most 2 decimal places"

    return True, None


def validate_file_extension(filename: str, allowed_extensions: list[str] | None = None) -> bool:
    """
    Validate file extension.

    Args:
        filename: Name of the file
        allowed_extensions: List of allowed extensions (defaults to config)

    Returns:
        True if valid, False otherwise
    """
    if not filename:
        return False

    if allowed_extensions is None:
        allowed_extensions = settings.allowed_upload_extensions

    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    return file_extension in allowed_extensions


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove or replace dangerous characters
    sanitized = re.sub(r'[^\w\-_\.]', '_', filename)

    # Remove multiple consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)

    # Remove leading/trailing underscores and dots
    sanitized = sanitized.strip('_.')

    return sanitized or 'unnamed_file'
