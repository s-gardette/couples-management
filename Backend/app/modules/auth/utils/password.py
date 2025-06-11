"""
Password utilities for the auth module.
"""

import re
from datetime import datetime
from uuid import UUID

from app.core.utils.security import verify_password
from app.core.utils.validators import validate_password_strength


def validate_password_strength_detailed(password: str) -> dict[str, any]:
    """
    Detailed password strength validation with scoring.

    Args:
        password: Password to validate

    Returns:
        Dictionary with validation results and detailed feedback
    """
    is_valid, errors = validate_password_strength(password)
    score = calculate_password_strength_score(password)

    return {
        "is_valid": is_valid,
        "errors": errors,
        "score": score,
        "level": get_strength_level(score),
        "suggestions": get_password_suggestions(password, errors)
    }


def calculate_password_strength_score(password: str) -> int:
    """
    Calculate password strength score (0-100).

    Args:
        password: Password to score

    Returns:
        Password strength score
    """
    score = 0

    # Length scoring (up to 25 points)
    length = len(password)
    if length >= 8:
        score += min(25, length * 2)

    # Character variety scoring (up to 40 points)
    if re.search(r'[a-z]', password):
        score += 10
    if re.search(r'[A-Z]', password):
        score += 10
    if re.search(r'\d', password):
        score += 10
    if re.search(r'[!@#$%^&*(),.?":{}|<>\-_=\[\]\\\/~`+]', password):
        score += 10

    # Pattern complexity (up to 20 points)
    # No repeated characters
    if not re.search(r'(.)\1{2,}', password):
        score += 5

    # No common patterns
    if not re.search(r'(123|abc|qwe|asd)', password.lower()):
        score += 5

    # Mixed case within word
    if re.search(r'[a-z][A-Z]|[A-Z][a-z]', password):
        score += 5

    # Numbers not just at end
    if re.search(r'\d.*[a-zA-Z]', password):
        score += 5

    # Uniqueness bonus (up to 15 points)
    unique_chars = len(set(password))
    score += min(15, unique_chars)

    return min(100, score)


def get_strength_level(score: int) -> str:
    """
    Get password strength level based on score.

    Args:
        score: Password strength score

    Returns:
        Strength level string
    """
    if score >= 80:
        return "very_strong"
    elif score >= 60:
        return "strong"
    elif score >= 40:
        return "medium"
    elif score >= 20:
        return "weak"
    else:
        return "very_weak"


def get_password_suggestions(password: str, errors: list[str]) -> list[str]:
    """
    Get password improvement suggestions.

    Args:
        password: Password to analyze
        errors: Validation errors

    Returns:
        List of improvement suggestions
    """
    suggestions = []

    if len(password) < 12:
        suggestions.append("Consider using at least 12 characters for better security")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_=\[\]\\\/~`+]', password):
        suggestions.append("Add special characters like !@#$%^&* for stronger security")

    if re.search(r'(.)\1{2,}', password):
        suggestions.append("Avoid repeating the same character multiple times")

    if re.search(r'(123|abc|qwe|asd|password|admin)', password.lower()):
        suggestions.append("Avoid common patterns and dictionary words")

    if password.lower() in ['password', '123456', 'admin', 'user']:
        suggestions.append("This password is too common - choose something unique")

    if not suggestions:
        suggestions.append("Your password meets the requirements!")

    return suggestions


def check_password_history(
    user_id: UUID,
    new_password: str,
    password_history: list[str],
    history_limit: int = 5
) -> tuple[bool, str | None]:
    """
    Check if password was used recently (optional password history tracking).

    Args:
        user_id: User UUID
        new_password: New password to check
        password_history: List of recent password hashes
        history_limit: Number of previous passwords to check

    Returns:
        Tuple of (is_allowed, error_message)
    """
    # Check against recent passwords
    for old_password_hash in password_history[-history_limit:]:
        if verify_password(new_password, old_password_hash):
            return False, "Password was used recently. Please choose a different password."

    return True, None


def generate_secure_password(
    length: int = 12,
    include_uppercase: bool = True,
    include_lowercase: bool = True,
    include_numbers: bool = True,
    include_special: bool = True,
    exclude_ambiguous: bool = True
) -> str:
    """
    Generate a secure password with specified criteria.

    Args:
        length: Password length
        include_uppercase: Include uppercase letters
        include_lowercase: Include lowercase letters
        include_numbers: Include numbers
        include_special: Include special characters
        exclude_ambiguous: Exclude ambiguous characters (0, O, l, 1, etc.)

    Returns:
        Generated secure password
    """
    import secrets
    import string

    if length < 8:
        length = 8

    # Build character sets
    chars = ""
    required_chars = []

    if include_lowercase:
        lowercase = string.ascii_lowercase
        if exclude_ambiguous:
            lowercase = lowercase.replace('l', '').replace('o', '')
        chars += lowercase
        required_chars.append(secrets.choice(lowercase))

    if include_uppercase:
        uppercase = string.ascii_uppercase
        if exclude_ambiguous:
            uppercase = uppercase.replace('I', '').replace('O', '')
        chars += uppercase
        required_chars.append(secrets.choice(uppercase))

    if include_numbers:
        numbers = string.digits
        if exclude_ambiguous:
            numbers = numbers.replace('0', '').replace('1', '')
        chars += numbers
        required_chars.append(secrets.choice(numbers))

    if include_special:
        special = "!@#$%^&*(),.?\":{}|<>\-_=\[\]\\\/~`+"
        chars += special
        required_chars.append(secrets.choice(special))

    # Generate remaining characters
    remaining_length = length - len(required_chars)
    password_chars = required_chars + [secrets.choice(chars) for _ in range(remaining_length)]

    # Shuffle the password
    secrets.SystemRandom().shuffle(password_chars)

    return ''.join(password_chars)


def is_password_compromised(password: str) -> bool:
    """
    Check if password appears in common breach databases (placeholder).

    Note: In a real implementation, this would check against services like
    HaveIBeenPwned API or local breach databases.

    Args:
        password: Password to check

    Returns:
        True if password is known to be compromised
    """
    # Common compromised passwords (basic check)
    common_passwords = {
        'password', '123456', '123456789', 'qwerty', 'abc123',
        'password123', 'admin', 'letmein', 'welcome', 'monkey',
        '1234567890', 'dragon', 'master', 'hello', 'freedom'
    }

    return password.lower() in common_passwords


def get_password_age_warning(last_changed: datetime, max_age_days: int = 90) -> str | None:
    """
    Check if password needs to be changed due to age.

    Args:
        last_changed: When password was last changed
        max_age_days: Maximum password age in days

    Returns:
        Warning message if password is old, None otherwise
    """
    age = datetime.utcnow() - last_changed

    if age.days > max_age_days:
        return f"Password is {age.days} days old. Consider changing it for security."
    elif age.days > max_age_days - 7:
        days_left = max_age_days - age.days
        return f"Password expires in {days_left} days. Consider changing it soon."

    return None


def validate_password_change(
    current_password: str,
    new_password: str,
    current_password_hash: str,
    password_history: list[str] | None = None
) -> dict[str, any]:
    """
    Comprehensive password change validation.

    Args:
        current_password: Current password
        new_password: New password
        current_password_hash: Hash of current password
        password_history: List of recent password hashes

    Returns:
        Validation result dictionary
    """
    result = {
        "is_valid": True,
        "errors": [],
        "warnings": []
    }

    # Verify current password
    if not verify_password(current_password, current_password_hash):
        result["is_valid"] = False
        result["errors"].append("Current password is incorrect")
        return result

    # Check if new password is same as current
    if current_password == new_password:
        result["is_valid"] = False
        result["errors"].append("New password must be different from current password")

    # Validate new password strength
    strength_result = validate_password_strength_detailed(new_password)
    if not strength_result["is_valid"]:
        result["is_valid"] = False
        result["errors"].extend(strength_result["errors"])

    # Check password history if provided
    if password_history:
        history_check, history_error = check_password_history(
            None, new_password, password_history
        )
        if not history_check:
            result["is_valid"] = False
            result["errors"].append(history_error)

    # Check for compromised password
    if is_password_compromised(new_password):
        result["warnings"].append("This password appears in known data breaches. Consider using a different password.")

    return result
