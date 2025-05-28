"""
Helper utilities for date/time, string manipulation, and other common tasks.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, ROUND_HALF_UP


def generate_uuid() -> str:
    """
    Generate a new UUID string.
    
    Returns:
        UUID string
    """
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """
    Get current UTC datetime.
    
    Returns:
        Current UTC datetime
    """
    return datetime.now(timezone.utc)


def format_currency(amount: Union[float, Decimal], currency: str = "USD") -> str:
    """
    Format amount as currency string.
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    if isinstance(amount, float):
        amount = Decimal(str(amount))
    
    # Round to 2 decimal places
    amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
    }
    
    symbol = currency_symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug.
    
    Args:
        text: Text to slugify
        
    Returns:
        Slugified text
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def parse_name(full_name: str) -> Dict[str, str]:
    """
    Parse full name into first and last name.
    
    Args:
        full_name: Full name string
        
    Returns:
        Dictionary with first_name and last_name
    """
    parts = full_name.strip().split()
    
    if len(parts) == 0:
        return {"first_name": "", "last_name": ""}
    elif len(parts) == 1:
        return {"first_name": parts[0], "last_name": ""}
    else:
        return {"first_name": parts[0], "last_name": " ".join(parts[1:])}


def calculate_percentage(part: Union[float, Decimal], total: Union[float, Decimal]) -> float:
    """
    Calculate percentage of part from total.
    
    Args:
        part: Part value
        total: Total value
        
    Returns:
        Percentage (0-100)
    """
    if total == 0:
        return 0.0
    
    return float((part / total) * 100)


def split_amount_equally(total_amount: Union[float, Decimal], num_people: int) -> List[Decimal]:
    """
    Split amount equally among people, handling rounding.
    
    Args:
        total_amount: Total amount to split
        num_people: Number of people to split among
        
    Returns:
        List of amounts for each person
    """
    if num_people <= 0:
        return []
    
    if isinstance(total_amount, float):
        total_amount = Decimal(str(total_amount))
    
    # Calculate base amount per person
    base_amount = total_amount / num_people
    base_amount = base_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Create list with base amounts
    amounts = [base_amount] * num_people
    
    # Calculate remainder and distribute
    total_distributed = base_amount * num_people
    remainder = total_amount - total_distributed
    
    # Distribute remainder cents
    remainder_cents = int(remainder * 100)
    for i in range(abs(remainder_cents)):
        if remainder_cents > 0:
            amounts[i % num_people] += Decimal('0.01')
        else:
            amounts[i % num_people] -= Decimal('0.01')
    
    return amounts


def mask_email(email: str) -> str:
    """
    Mask email address for privacy.
    
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


def clean_dict(data: Dict[str, Any], remove_none: bool = True, remove_empty: bool = False) -> Dict[str, Any]:
    """
    Clean dictionary by removing None or empty values.
    
    Args:
        data: Dictionary to clean
        remove_none: Remove None values
        remove_empty: Remove empty strings/lists/dicts
        
    Returns:
        Cleaned dictionary
    """
    cleaned = {}
    
    for key, value in data.items():
        if remove_none and value is None:
            continue
        
        if remove_empty and value in ('', [], {}):
            continue
        
        cleaned[key] = value
    
    return cleaned


def get_initials(name: str) -> str:
    """
    Get initials from a name.
    
    Args:
        name: Full name
        
    Returns:
        Initials (max 2 characters)
    """
    if not name:
        return ""
    
    words = name.strip().split()
    if len(words) == 1:
        return words[0][0].upper()
    else:
        return (words[0][0] + words[-1][0]).upper() 